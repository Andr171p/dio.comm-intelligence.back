from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import count

from src.domain.communications.vo import TranscriptRepresentation, TranscriptSegment

from .chunking import AudioChunk

UNKNOWN_SPEAKER = "UNKNOWN"

_MIN_SPEAKER_OVERLAP_MS = 300


@dataclass(frozen=True, slots=True)
class ChunkTranscript:
    """Транскрипт фрагмента, таймкоды относительно начала фрагмента."""

    chunk: AudioChunk
    transcript: TranscriptRepresentation


def _shift(ms: int | None, offset_ms: int) -> int | None:
    return None if ms is None else ms + offset_ms


def _to_absolute(item: ChunkTranscript) -> list[TranscriptSegment]:
    offset_ms = item.chunk.start_ms
    return [
        replace(
            segment,
            started_ms=_shift(segment.started_ms, offset_ms),
            ended_ms=_shift(segment.ended_ms, offset_ms),
        )
        for segment in item.transcript.segments
    ]


def _midpoint(segment: TranscriptSegment) -> int | None:
    bounds = [ms for ms in (segment.started_ms, segment.ended_ms) if ms is not None]
    return sum(bounds) // len(bounds) if bounds else None


def _is_owned(segment: TranscriptSegment, chunk: AudioChunk, *, is_last: bool) -> bool:
    """Сегмент принадлежит фрагменту, если его середина попадает в собственный интервал."""

    if (midpoint := _midpoint(segment)) is None:
        return True

    return chunk.own_from_ms <= midpoint and (midpoint < chunk.own_to_ms or is_last)


def _overlap_ms(a: TranscriptSegment, b: TranscriptSegment) -> int:
    match a.started_ms, a.ended_ms, b.started_ms, b.ended_ms:
        case int(a_start), int(a_end), int(b_start), int(b_end):
            return max(0, min(a_end, b_end) - max(a_start, b_start))

    return 0


def _link_speakers(
    previous: Sequence[TranscriptSegment],
    current: Sequence[TranscriptSegment],
) -> dict[str, str]:
    """Сопоставляет локальные метки спикеров фрагмента с глобальными метками предыдущего.

    Пары спикеров ранжируются по суммарному времени одновременного звучания в зоне
    перекрытия и назначаются жадно, один к одному.
    """

    scores: Counter[tuple[str, str]] = Counter()
    for prev in previous:
        for cur in current:
            if UNKNOWN_SPEAKER not in {prev.speaker, cur.speaker}:
                scores[prev.speaker, cur.speaker] += _overlap_ms(prev, cur)

    mapping: dict[str, str] = {}
    for (global_speaker, local_speaker), score in scores.most_common():
        if score < _MIN_SPEAKER_OVERLAP_MS:
            break

        if local_speaker not in mapping and global_speaker not in mapping.values():
            mapping[local_speaker] = global_speaker

    return mapping


def merge_transcripts(items: Sequence[ChunkTranscript]) -> TranscriptRepresentation:
    """Склеивает транскрипты фрагментов в единый транскрипт записи.

    - таймкоды переводятся в абсолютные;
    - из зоны перекрытия берутся сегменты фрагмента, которому принадлежит их середина;
    - метки спикеров сквозные (SPEAKER_00, SPEAKER_01, ...): локальные метки фрагмента
      сопоставляются с метками предыдущего по зоне перекрытия, остальные получают новые.
    """

    labels = (f"SPEAKER_{number:02}" for number in count())
    merged: list[TranscriptSegment] = []
    previous: list[TranscriptSegment] = []

    for index, item in enumerate(items):
        segments = _to_absolute(item)
        mapping = _link_speakers(previous, segments)

        for segment in segments:
            if segment.speaker != UNKNOWN_SPEAKER and segment.speaker not in mapping:
                mapping[segment.speaker] = next(labels)

        previous = [
            replace(segment, speaker=mapping.get(segment.speaker, segment.speaker)) for segment in segments
        ]
        is_last = index == len(items) - 1
        merged.extend(segment for segment in previous if _is_owned(segment, item.chunk, is_last=is_last))

    languages = Counter(item.transcript.language for item in items if item.transcript.language)
    return TranscriptRepresentation(
        segments=tuple(replace(segment, id=str(index)) for index, segment in enumerate(merged)),
        language=languages.most_common(1)[0][0] if languages else None,
    )


__all__ = ["UNKNOWN_SPEAKER", "ChunkTranscript", "merge_transcripts"]
