from src.application.transcription import (
    UNKNOWN_SPEAKER,
    AudioChunk,
    ChunkTranscript,
    merge_transcripts,
    plan_chunks,
    render_text,
)
from src.domain.communications.vo import TranscriptRepresentation, TranscriptSegment


def _segment(speaker: str, text: str, started_ms: int, ended_ms: int) -> TranscriptSegment:
    return TranscriptSegment(
        id="0", speaker=speaker, text=text, started_ms=started_ms, ended_ms=ended_ms, confidence=0.9,
    )


# ===========================================================================================================
# plan_chunks
# ===========================================================================================================


def test_short_record_is_not_split() -> None:
    chunks = plan_chunks(70_000, [], target_ms=60_000, overlap_ms=5_000, search_ms=15_000)

    assert chunks == (AudioChunk(index=0, start_ms=0, end_ms=70_000, own_from_ms=0, own_to_ms=70_000),)


def test_cuts_in_the_middle_of_the_longest_nearby_silence() -> None:
    silences = [(50_000, 50_500), (58_000, 60_000), (66_000, 66_400)]

    first, second = plan_chunks(100_000, silences, target_ms=60_000, overlap_ms=5_000, search_ms=15_000)

    assert first.own_to_ms == second.own_from_ms == 59_000
    assert (first.end_ms, second.start_ms) == (64_000, 54_000)


def test_cuts_at_target_without_silence() -> None:
    chunks = plan_chunks(190_000, [], target_ms=60_000, overlap_ms=5_000, search_ms=15_000)

    assert [chunk.own_from_ms for chunk in chunks] == [0, 60_000, 120_000]
    assert chunks[-1].own_to_ms == chunks[-1].end_ms == 190_000


# ===========================================================================================================
# merge_transcripts
# ===========================================================================================================


def test_merge_deduplicates_overlap_and_links_speakers() -> None:
    first = AudioChunk(index=0, start_ms=0, end_ms=65_000, own_from_ms=0, own_to_ms=60_000)
    second = AudioChunk(index=1, start_ms=55_000, end_ms=120_000, own_from_ms=60_000, own_to_ms=120_000)

    first_transcript = TranscriptRepresentation(
        segments=(
            _segment("SPEAKER_01", "Привет", 1_000, 5_000),
            _segment("SPEAKER_00", "Здравствуйте", 6_000, 20_000),
            _segment("SPEAKER_01", "до стыка", 56_000, 59_000),
            _segment("SPEAKER_00", "после стыка", 61_000, 64_000),
        ),
        language="ru",
    )
    # Таймкоды относительно начала второго фрагмента, метки спикеров переставлены
    second_transcript = TranscriptRepresentation(
        segments=(
            _segment("SPEAKER_00", "до стыка", 1_000, 4_000),
            _segment("SPEAKER_01", "после стыка", 6_000, 9_000),
            _segment("SPEAKER_02", "новый спикер", 30_000, 35_000),
        ),
        language="ru",
    )

    merged = merge_transcripts(
        [ChunkTranscript(first, first_transcript), ChunkTranscript(second, second_transcript)],
    )

    assert [(s.speaker, s.text, s.started_ms) for s in merged.segments] == [
        ("SPEAKER_00", "Привет", 1_000),
        ("SPEAKER_01", "Здравствуйте", 6_000),
        ("SPEAKER_00", "до стыка", 56_000),
        ("SPEAKER_01", "после стыка", 61_000),
        ("SPEAKER_02", "новый спикер", 85_000),
    ]
    assert [s.id for s in merged.segments] == ["0", "1", "2", "3", "4"]
    assert merged.language == "ru"


def test_merge_keeps_unknown_speaker_label() -> None:
    chunk = AudioChunk(index=0, start_ms=0, end_ms=10_000, own_from_ms=0, own_to_ms=10_000)
    transcript = TranscriptRepresentation(segments=(_segment(UNKNOWN_SPEAKER, "шум", 0, 1_000),))

    merged = merge_transcripts([ChunkTranscript(chunk, transcript)])

    assert merged.segments[0].speaker == UNKNOWN_SPEAKER


# ===========================================================================================================
# render_text
# ===========================================================================================================


def test_render_groups_consecutive_segments_of_speaker() -> None:
    transcript = TranscriptRepresentation(
        segments=(
            _segment("SPEAKER_00", "Добрый день.", 3_000, 4_000),
            _segment("SPEAKER_00", "Начнём.", 4_500, 5_000),
            _segment("SPEAKER_01", "Да.", 3_725_000, 3_726_000),
        ),
        language="ru",
    )

    text = render_text(transcript)

    assert text.content == "[00:00:03] SPEAKER_00: Добрый день. Начнём.\n[01:02:05] SPEAKER_01: Да."
    assert text.language == "ru"
