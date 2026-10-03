import os
from bisect import bisect_right
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from itertools import groupby
from operator import itemgetter
from statistics import fmean

import aiohttp
from anyio import Path

from src.application.recognizer import RecognitionOptions
from src.domain.communications.vo import TranscriptSegment

from .config import WhisperConfig
from .dtos import WhisperResponse, WhisperSegment

_UNKNOWN_SPEAKER = "UNKNOWN"


def _convert_seconds_to_ms(seconds: float | None) -> int | None:
    return round(seconds * 1000) if seconds is not None else None


def _split_segment(segment: WhisperSegment, boundaries: Sequence[float]) -> list[WhisperSegment]:
    """Разрезает сегмент по границам (в секундах) по таймкодам слов."""

    intervals: list[int | None] = []
    for word in segment.words:
        if word.start is not None and word.end is not None:
            intervals.append(bisect_right(boundaries, (word.start + word.end) / 2))
        else:  # слова без таймкодов (например, числа) относим к предыдущему слову
            intervals.append(intervals[-1] if intervals else None)

    groups = [
        [word for _, word in group]
        for _, group in groupby(zip(intervals, segment.words, strict=True), key=itemgetter(0))
    ]
    if len(groups) <= 1:
        return [segment]

    return [
        WhisperSegment(
            start=next((word.start for word in words if word.start is not None), segment.start),
            end=next((word.end for word in reversed(words) if word.end is not None), segment.end),
            text=" ".join(word.word.strip() for word in words),
            speaker=segment.speaker,
            words=words,
        )
        for words in groups
    ]


def _build_transcript_segment(segment: WhisperSegment, *, id: int) -> TranscriptSegment:
    """Преобразует распознанный сегмент от Whisper в контракт приложения."""

    speaker = (
        segment.speaker or
        next((word.speaker for word in segment.words if word.speaker is not None), _UNKNOWN_SPEAKER)
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
    async def _get_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        yield self._session

    async def recognize(
        self,
        audio: os.PathLike[str],
        options: RecognitionOptions | None = None,
    ) -> tuple[TranscriptSegment, ...]:
        path = Path(audio)
        options = options or RecognitionOptions(filename=path.name)

        form_data = aiohttp.FormData()
        form_data.add_field(
            name="audio_file",
            value=await path.read_bytes(),
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
            self._get_session() as session,
            session.post("/asr", params=params, data=form_data) as response,
        ):
            response.raise_for_status()
            raw_data = await response.text()

        result = WhisperResponse.model_validate_json(raw_data)
        boundaries = sorted(ms / 1000 for ms in options.split_at_ms)
        segments = [part for segment in result.segments for part in _split_segment(segment, boundaries)]

        return tuple(_build_transcript_segment(segment, id=i) for i, segment in enumerate(segments))

    async def close(self) -> None:
        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None
