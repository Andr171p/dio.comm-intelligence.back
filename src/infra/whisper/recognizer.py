from collections.abc import AsyncIterator, Buffer, Sequence
from contextlib import asynccontextmanager
from statistics import fmean

import aiohttp

from src.application.recognizer import RecognitionOptions
from src.domain.communications.vo import TranscriptSegment

from .config import WhisperConfig
from .dtos import WhisperResponse, WhisperSegment


def _convert_seconds_to_ms(seconds: float | None) -> int | None:
    return round(seconds * 1000) if seconds is not None else None


def _build_transcript_segment(segment: WhisperSegment, *, id: int) -> TranscriptSegment:
    """Преобразует распознанный сегмент от Whisper в контракт приложения."""

    speaker = (
        segment.speaker or
        next((word.speaker for word in segment.words if word.speaker is not None), "UNKNOWN")
    )
    scores = [word.score for word in segment.words if word.score is not None]

    return TranscriptSegment(
        id=str(segment.id) if segment.id is not None else str(id),
        speaker=speaker,
        text=segment.text.strip(),
        started_ms=_convert_seconds_to_ms(segment.start),
        ended_ms=_convert_seconds_to_ms(segment.end),
        confidence=fmean(scores) if scores else 0.0,
    )


class WhisperRecognizer:
    def __init__(self, config: WhisperConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

    @asynccontextmanager
    async def _get_client_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        yield self._session

    async def recognize(
        self,
        audio: Buffer,
        options: RecognitionOptions | None = None,
    ) -> Sequence[TranscriptSegment]:
        form_data = aiohttp.FormData()
        form_data.add_field(
            name="audio_file",
            value=bytes(memoryview(audio)),
            filename=options.filename,
            content_type=options.content_type,
        )

        params: dict[str, int | str] = {
            "task": "transcribe",
            "output": "json",
            "encode": "true",
            "diarize": str(options.diarize).lower()
        }

        if options.language is not None:
            params["language"] = options.language

        if options.min_speakers is not None:
            params["min_speakers"] = options.min_speakers

        if options.max_speakers is not None:
            params["max_speakers"] = options.max_speakers

        async with (
            self._get_client_session() as session,
            session.post("/asr", params=params, data=form_data) as response,
        ):
            response.raise_for_status()
            raw_data = await response.text()

        result = WhisperResponse.model_validate_json(raw_data)
        return tuple(
            _build_transcript_segment(segment, id=i)
            for i, segment in enumerate(result.segments)
        )

    async def close(self) -> None:
        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None
