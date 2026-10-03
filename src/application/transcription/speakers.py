from dataclasses import replace
from functools import cache

from src.domain.communications.vo import TranscriptSegment

from .dtos import RecognizedAudioChunk, SpeakerResolutionOptions

type Interval = tuple[int, int]


def resolve_speakers(
    chunks: tuple[RecognizedAudioChunk, ...],
    *,
    options: SpeakerResolutionOptions | None = None,
) -> tuple[RecognizedAudioChunk, ...]:
    """Разрешает локальные speaker labels в глобальные.

    Каждый ASR request может независимо назначать speaker labels:

        chunk 0: A, B
        chunk 1: A, B
        chunk 2: A, B

    При этом одинаковая буква не гарантирует одного физического
    человека.

    Алгоритм использует временной overlap соседних recognition chunks
    и сопоставляет speaker labels по совпадению речевой активности.

    Если соответствие нельзя надёжно определить, создаётся новый
    global speaker.
    """

    if not chunks:
        return ()

    options = options or SpeakerResolutionOptions()

    ordered = sorted(chunks, key=lambda x: x.chunk.index)

    resolved: list[RecognizedAudioChunk] = []

    next_speaker_id = 0

    # Первый чанк задаёт initial global speakers.

    first = ordered[0]
    first_mapping: dict[str, str] = {}

    for speaker in _speakers_by_first_appearance(first.segments):
        first_mapping[speaker] = f"speaker_{next_speaker_id}"
        next_speaker_id += 1

    first_resolved = _apply_mapping(first, first_mapping)

    resolved.append(first_resolved)

    # Следующие чанки сопоставляются с уже разрешённой историей.

    for current in ordered[1:]:
        mapping = _resolve_chunk_mapping(
            previous=resolved[-1],
            current=current,
            options=options,
        )

        # Speaker labels, которые не удалось доказано связать
        # с предыдущим chunk, получают новый global id.

        for speaker in _speakers_by_first_appearance(current.segments):
            if speaker in mapping:
                continue

            mapping[speaker] = f"speaker_{next_speaker_id}"
            next_speaker_id += 1

        resolved.append(_apply_mapping(current, mapping))

    return tuple(resolved)


def _resolve_chunk_mapping(
    *,
    previous: RecognizedAudioChunk,
    current: RecognizedAudioChunk,
    options: SpeakerResolutionOptions,
) -> dict[str, str]:
    overlap_start = max(previous.chunk.start_ms, current.chunk.start_ms)
    overlap_end = min(previous.chunk.end_ms, current.chunk.end_ms)

    if overlap_start >= overlap_end:
        return {}

    previous_intervals = _group_speaker_intervals(
        previous.segments,
        start_ms=overlap_start,
        end_ms=overlap_end,
    )

    current_intervals = _group_speaker_intervals(
        current.segments,
        start_ms=overlap_start,
        end_ms=overlap_end,
    )

    weights: dict[tuple[str, str], int] = {}

    for current_speaker, current_spans in current_intervals.items():
        for global_speaker, previous_spans in previous_intervals.items():
            shared_ms = _intersection_duration(current_spans, previous_spans,)

            if shared_ms < options.min_shared_speech_ms:
                continue

            current_duration = _total_duration(current_spans)
            previous_duration = _total_duration(previous_spans)

            denominator = current_duration + previous_duration

            if denominator == 0:
                continue

            similarity = 2 * shared_ms / denominator

            if similarity < options.min_similarity:
                continue

            # Absolute shared speech duration is used as the
            # optimization weight. Similarity already acts as
            # the quality threshold above.
            weights[(current_speaker, global_speaker)] = shared_ms

    return _maximum_weight_mapping(weights)


def _group_speaker_intervals(
    segments: tuple[TranscriptSegment, ...],
    *,
    start_ms: int,
    end_ms: int,
) -> dict[str, tuple[Interval, ...]]:
    grouped: dict[str, list[Interval]] = {}

    for segment in segments:
        if (
            segment.speaker is None
            or segment.started_ms is None
            or segment.ended_ms is None
        ):
            continue

        start = max(
            segment.started_ms,
            start_ms,
        )

        end = min(
            segment.ended_ms,
            end_ms,
        )

        if start >= end:
            continue

        grouped.setdefault(
            segment.speaker,
            [],
        ).append((start, end))

    return {
        speaker: _merge_intervals(intervals)
        for speaker, intervals in grouped.items()
    }


def _merge_intervals(intervals: list[Interval],) -> tuple[Interval, ...]:
    if not intervals:
        return ()

    ordered = sorted(intervals)
    result: list[Interval] = []
    current_start, current_end = ordered[0]

    for start, end in ordered[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
            continue

        result.append((current_start, current_end))

        current_start = start
        current_end = end

    result.append((current_start, current_end))

    return tuple(result)


def _intersection_duration(left: tuple[Interval, ...], right: tuple[Interval, ...]) -> int:
    total = 0
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        left_start, left_end = left[left_index]
        right_start, right_end = right[right_index]

        total += max(0, min(left_end, right_end) - max(left_start, right_start))

        if left_end <= right_end:
            left_index += 1
        else:
            right_index += 1

    return total


def _total_duration(intervals: tuple[Interval, ...]) -> int:
    return sum(end - start for start, end in intervals)


def _maximum_weight_mapping(weights: dict[tuple[str, str], int]) -> dict[str, str]:
    if not weights:
        return {}

    current_speakers = sorted({current for current, _ in weights})

    global_speakers = sorted({global_speaker for _, global_speaker in weights})

    global_indexes = {speaker: index for index, speaker in enumerate(global_speakers)}

    @cache
    def solve(current_index: int, used_mask: int) -> tuple[int, tuple[tuple[str, str], ...]]:
        if current_index >= len(current_speakers):
            return 0, ()

        current_speaker = current_speakers[current_index]

        best_weight, best_mapping = solve(current_index + 1, used_mask)

        for global_speaker in global_speakers:
            weight = weights.get((current_speaker, global_speaker))

            if weight is None:
                continue

            bit = (1 << global_indexes[global_speaker])

            if used_mask & bit:
                continue

            next_weight, next_mapping = solve(current_index + 1, used_mask | bit)
            candidate_weight = weight + next_weight
            candidate_mapping = ((current_speaker, global_speaker), *next_mapping)

            if candidate_weight > best_weight:
                best_weight = candidate_weight
                best_mapping = candidate_mapping

        return best_weight, best_mapping

    _, mapping = solve(0, 0)
    return dict(mapping)


def _apply_mapping(chunk: RecognizedAudioChunk, mapping: dict[str, str]) -> RecognizedAudioChunk:
    return RecognizedAudioChunk(
        chunk=chunk.chunk,
        segments=tuple(
            replace(
                segment,
                speaker=(
                    mapping.get(segment.speaker, segment.speaker)
                    if segment.speaker is not None
                    else None
                ),
            )
            for segment in chunk.segments
        ),
    )


def _speakers_by_first_appearance(segments: tuple[TranscriptSegment, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    ordered = sorted(
        segments,
        key=lambda s: s.started_ms if s.started_ms is not None else 2**63,
    )

    for segment in ordered:
        speaker = segment.speaker

        if speaker is None or speaker in seen:
            continue

        seen.add(speaker)
        result.append(speaker)

    return tuple(result)
