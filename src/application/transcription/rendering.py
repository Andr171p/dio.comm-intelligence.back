from itertools import groupby
from operator import attrgetter

from src.domain.communications.vo import TextRepresentation, TranscriptRepresentation


def _format_timestamp(ms: int) -> str:
    hours, rest = divmod(ms // 1000, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def render_text(transcript: TranscriptRepresentation) -> TextRepresentation:
    """Представляет транскрипт сплошным текстом в LLM-ready формате.

    Подряд идущие сегменты одного спикера объединяются в реплику::

        [00:00:03] SPEAKER_00: Добрый день, коллеги.
        [00:00:07] SPEAKER_01: Здравствуйте.
    """

    lines: list[str] = []

    for speaker, group in groupby(transcript.segments, key=attrgetter("speaker")):
        segments = list(group)
        if not (text := " ".join(segment.text for segment in segments if segment.text)):
            continue

        started_ms = segments[0].started_ms
        timestamp = f"[{_format_timestamp(started_ms)}] " if started_ms is not None else ""
        lines.append(f"{timestamp}{speaker}: {text}")

    return TextRepresentation(content="\n".join(lines), language=transcript.language)


__all__ = ["render_text"]
