"""Обработка аудио через ffmpeg (системная зависимость воркера)."""

import asyncio
import re
from pathlib import Path

from src.application.transcription import Silence

_SAMPLE_RATE = 16_000

_SILENCE_START = re.compile(r"silence_start: (?P<value>\d+(?:\.\d+)?)")
_SILENCE_END = re.compile(r"silence_end: (?P<value>\d+(?:\.\d+)?)")


class FFmpegError(RuntimeError):
    pass


async def _run(*args: str) -> tuple[str, str]:
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise

    if process.returncode != 0:
        details = stderr.decode(errors="replace")[-2000:]
        raise FFmpegError(f"{args[0]} exited with code {process.returncode}: {details}")

    return stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def extract_audio(source: str, target: Path, *, audio_filter: str | None = None) -> None:
    """Извлекает дорожку в моно 16 кГц FLAC (формат Whisper) с опциональной фильтрацией.

    ``source`` может быть путём или URL (ffmpeg читает потоково, видео целиком не скачивается).
    """

    filter_args = ("-af", audio_filter) if audio_filter else ()
    await _run(
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-i", source,
        "-vn", "-ac", "1", "-ar", str(_SAMPLE_RATE), *filter_args,
        "-c:a", "flac", str(target),
    )


async def probe_duration_ms(path: Path) -> int:
    stdout, _ = await _run(
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path),
    )
    return round(float(stdout.strip()) * 1000)


async def detect_silences(path: Path, *, noise_db: float, min_duration_ms: int) -> list[Silence]:
    """Находит паузы тише ``noise_db`` дольше ``min_duration_ms``."""

    _, stderr = await _run(
        "ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration_ms / 1000}",
        "-f", "null", "-",
    )

    starts = [round(float(match["value"]) * 1000) for match in _SILENCE_START.finditer(stderr)]
    ends = [round(float(match["value"]) * 1000) for match in _SILENCE_END.finditer(stderr)]
    return list(zip(starts, ends, strict=False))


async def cut(source: Path, target: Path, *, start_ms: int, end_ms: int) -> None:
    await _run(
        "ffmpeg", "-hide_banner", "-nostdin", "-y",
        "-ss", f"{start_ms / 1000:.3f}", "-i", str(source), "-t", f"{(end_ms - start_ms) / 1000:.3f}",
        "-c:a", "flac", str(target),
    )


__all__ = ["FFmpegError", "cut", "detect_silences", "extract_audio", "probe_duration_ms"]
