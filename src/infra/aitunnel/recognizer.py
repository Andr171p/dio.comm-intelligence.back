import os

from openai import AsyncOpenAI
from openai.types.audio import TranscriptionDiarized, TranscriptionDiarizedSegment

from src.application.recognizer import RecognitionOptions
from src.domain.communications.vo import TranscriptSegment

from .config import AiTunnelRecognizerConfig


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

        with open(audio, mode="rb") as file:  # noqa: ASYNC230
            # noinspection PyArgumentList
            result = await self._client.audio.translations.create(
                file=file,
                model=self._config.model,
                response_format="diarized_json",
                chunking_strategy="auto",
                **{"language": options.language} if options is not None else {},
            )

        if not isinstance(result, TranscriptionDiarized):
            raise RuntimeError(f"Expected diarized transcription response, got {type(result).__name__}")

        return tuple(_build_transcript_segment(segment) for segment in result.segments)


def _seconds_to_ms(seconds: float) -> int:
    return round(seconds * 1000)


def _build_transcript_segment(segment: TranscriptionDiarizedSegment) -> TranscriptSegment:
    return TranscriptSegment(
        id=segment.id,
        speaker=segment.speaker,
        text=segment.text.strip(),
        started_ms=_seconds_to_ms(segment.start),
        ended_ms=_seconds_to_ms(segment.end),
        confidence=None,
    )
