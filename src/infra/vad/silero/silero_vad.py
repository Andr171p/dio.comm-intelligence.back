from typing import BinaryIO

from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, Popen

import numpy as np

from src.infra.vad.silero.config import VadConfig
from src.infra.vad.exceptions import VadError
from src.infra.vad.silero.model import SileroOnnxModel, SileroOnnxStream


def _read_frame(stream: BinaryIO, size: int) -> bytes | None:
    """Прочитать ровно один PCM frame.

    Последний неполный frame дополняется нулями, чтобы модель всегда
    получала ожидаемые 512 samples.
    """
    buffer = bytearray()

    while len(buffer) < size:
        chunk = stream.read(size - len(buffer))

        if not chunk:
            break

        buffer.extend(chunk)

    if not buffer:
        return None

    if len(buffer) < size:
        buffer.extend(
            b"\x00" * (size - len(buffer))
        )

    return bytes(buffer)


def _pcm16_to_float32(data: bytes, *, expected_samples: int) -> np.ndarray:
    """Преобразовывает signed PCM16 LE в normalized float32."""

    samples = np.frombuffer(data, dtype="<i2")

    if len(samples) != expected_samples:
        raise VadError(f"Expected {expected_samples} PCM samples, got {len(samples)}")

    return samples.astype(np.float32, copy=True) / 32768.0


def _samples_to_ms(samples: int, sample_rate: int) -> int:
    return round(samples * 1000 / sample_rate)


@dataclass(frozen=True, slots=True)
class _SpeechEvent:
    """Изменение состояния речи в абсолютных samples."""

    start: int | None = None
    end: int | None = None


class _VadStateMachine:
    """Преобразует вероятности Silero в начало/конец речи."""

    def __init__(self, config: VadConfig) -> None:
        self._config = config

        self._min_silence_samples = round(config.sample_rate * config.min_silence_duration_ms / 1000)
        self._speech_pad_samples = round(config.sample_rate * config.speech_pad_ms / 1000)

        self._triggered = False
        self._temporary_end = 0
        self._current_sample = 0

    def process(self, *, probability: float, window_samples: int) -> _SpeechEvent | None:
        """Обрабатывает вероятность речи следующего audio frame."""

        self._current_sample += window_samples

        if probability >= self._config.threshold and self._temporary_end:
            self._temporary_end = 0

        if probability >= self._config.threshold and not self._triggered:
            self._triggered = True
            start = max(0, self._current_sample - self._speech_pad_samples - window_samples)
            return _SpeechEvent(start=start)

        if probability < self._config.negative_threshold and self._triggered:
            if not self._temporary_end:
                self._temporary_end = self._current_sample

            silence_duration = self._current_sample - self._temporary_end

            if silence_duration < self._min_silence_samples:
                return None

            end = self._temporary_end + self._speech_pad_samples - window_samples

            self._temporary_end = 0
            self._triggered = False

            return _SpeechEvent(end=max(0, end))

        return None


class SileroVad:
    """Потоковый Voice Activity Detector на базе Silero ONNX.

    FFmpeg декодирует произвольный входной media-файл в mono PCM
    16 kHz и передаёт его через stdout.

    Аудио обрабатывается небольшими окнами и полностью в память
    не загружается. В результате возвращаются безопасные абсолютные
    временные позиции, расположенные примерно посередине пауз между
    речевыми участками.
    """

    _BYTES_PER_SAMPLE = 2

    def __init__(self, config: VadConfig) -> None:
        self._config = config
        self._model = SileroOnnxModel(str(config.model_path))

    def detect_boundaries(self, audio: Path,) -> tuple[int, ...]:
        """Находит безопасные точки разбиения аудиозаписи.

        Args:
            audio: Локальный путь до исходной или подготовленной
                аудиозаписи. Формат файла определяется FFmpeg.

        Returns:
            Отсортированные абсолютные позиции в миллисекундах,
            подходящие для последующего chunk planning.

        Raises:
            VadError: Если FFmpeg или ONNX inference завершились с ошибкой.
        """
        stream = self._model.create_stream()

        state = _VadStateMachine(self._config)

        process = self._open_ffmpeg(audio)

        if process.stdout is None:
            process.kill()
            raise VadError("FFmpeg stdout is unavailable")

        try:
            boundaries = self._process_stream(process.stdout, stream, state)

            return_code = process.wait()

            if return_code != 0:
                stderr = process.stderr.read() if process.stderr is not None else b""

                raise VadError(f"FFmpeg VAD decoding failed: {stderr.decode(errors='replace')}")

            return tuple(boundaries)

        except Exception:
            if process.poll() is None:
                process.kill()
                process.wait()

            raise

        finally:
            if process.stdout is not None:
                process.stdout.close()

            if process.stderr is not None:
                process.stderr.close()

    def _open_ffmpeg(self, audio: Path) -> Popen[bytes]:
        """Открывает FFmpeg как поток mono PCM 16 kHz."""
        return Popen(
            [
                self._config.ffmpeg_path,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostats",

                "-i",
                str(audio),

                "-map",
                "0:a:0",
                "-vn",

                "-ac",
                "1",

                "-ar",
                str(self._config.sample_rate),

                "-f",
                "s16le",

                "-acodec",
                "pcm_s16le",

                "pipe:1",
            ],
            stdout=PIPE,
            stderr=PIPE,
            bufsize=0,
        )

    def _process_stream(
        self,
        audio: BinaryIO,
        model: SileroOnnxStream,
        state: _VadStateMachine,
    ) -> list[int]:
        """Последовательно обрабатывает PCM stream."""

        window_samples = model.WINDOW_SAMPLES

        frame_bytes = window_samples * self._BYTES_PER_SAMPLE
        boundaries: list[int] = []
        previous_speech_end: int | None = None

        while frame := _read_frame(audio, frame_bytes,):
            samples = _pcm16_to_float32(frame, expected_samples=window_samples,)

            probability = model.predict(samples)

            event = state.process(probability=probability, window_samples=window_samples)

            if event is None:
                continue

            if event.end is not None:
                previous_speech_end = event.end
                continue

            if (
                event.start is not None
                and previous_speech_end is not None
                and event.start > previous_speech_end
            ):
                boundary_sample = (previous_speech_end + event.start) // 2
                boundaries.append(_samples_to_ms(boundary_sample, self._config.sample_rate))
                previous_speech_end = None

        return boundaries
