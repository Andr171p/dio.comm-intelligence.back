from src.application.audio_chunking import AudioChunkRef
from src.domain.communications.vo import TranscriptSegment

from .dtos import RecognizedAudioChunk, SpeakerResolutionOptions
from .speakers import resolve_speakers


def build_transcript_segments(
    chunks: tuple[RecognizedAudioChunk, ...],
    *,
    speaker_options: SpeakerResolutionOptions | None = None,
) -> tuple[TranscriptSegment, ...]:
    """Строит транскрипт сегменты и разрешает локальных спикеров в глобальных."""

    resolved = resolve_speakers(chunks, options=speaker_options)
    result: list[TranscriptSegment] = []

    result.extend(
        chunk
        for chunk in resolved
        for segment in chunk.segments
        if _is_accepted_segment(segment, chunk.chunk)
    )
    result.sort(
        key=lambda s: (
            s.started_ms if s.started_ms is not None else 2 ** 63,
            s.ended_ms if s.ended_ms is not None else 2 ** 63,
        )
    )

    return tuple(result)


def _is_accepted_segment(segment: TranscriptSegment, chunk: AudioChunkRef) -> bool:
    if segment.started_ms is None or segment.ended_ms is None:
        return True

    midpoint = (segment.started_ms + segment.ended_ms) // 2

    return chunk.accepted_start_ms <= midpoint < chunk.accepted_end_ms
