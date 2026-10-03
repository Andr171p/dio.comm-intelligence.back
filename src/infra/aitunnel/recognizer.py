import os

from openai import AsyncOpenAI, omit
from openai.types.audio import TranscriptionDiarized, TranscriptionVerbose

from src.application.recognizer import RecognitionOptions
from src.domain.communications.vo import TranscriptSegment

from .config import AiTunnelRecognizerConfig

_UNKNOWN_SPEAKER = "unknown"


class AiTunnelRecognizer:
    def __init__(self, config: AiTunnelRecognizerConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value(),
            base_url=str(config.base_url),
            timeout=config.timeout,
        )

    async def recognize(
        self,
        audio: os.PathLike[str],
        options: RecognitionOptions | None = None,
    ) -> tuple[TranscriptSegment, ...]:
        language = (options.language if options is not None else None) or self._config.language

        # SDK сам асинхронно читает файл по пути
        if self._config.diarization:
            diarized = await self._client.audio.transcriptions.create(
                file=audio,
                model=self._config.model,
                response_format="diarized_json",
                chunking_strategy="auto",
                language=language or omit,
                stream=False,
            )
            if not isinstance(diarized, TranscriptionDiarized):
                raise RuntimeError(f"Expected diarized transcription, got {type(diarized).__name__}")

            return tuple(
                _build_transcript_segment(
                    segment.id, segment.speaker, segment.text, start=segment.start, end=segment.end,
                )
                for segment in diarized.segments
            )

        verbose = await self._client.audio.transcriptions.create(
            file=audio,
            model=self._config.model,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            language=language or omit,
        )
        if not isinstance(verbose, TranscriptionVerbose):
            raise RuntimeError(f"Expected verbose transcription, got {type(verbose).__name__}")

        return tuple(
            _build_transcript_segment(
                str(segment.id), _UNKNOWN_SPEAKER, segment.text, start=segment.start, end=segment.end,
            )
            for segment in verbose.segments or ()
        )

    async def close(self) -> None:
        await self._client.close()


def _seconds_to_ms(seconds: float) -> int:
    return round(seconds * 1000)


def _build_transcript_segment(
    id: str, speaker: str, text: str, *, start: float, end: float,
) -> TranscriptSegment:
    return TranscriptSegment(
        id=id,
        speaker=speaker,
        text=text.strip(),
        started_ms=_seconds_to_ms(start),
        ended_ms=_seconds_to_ms(end),
        confidence=None,
    )
