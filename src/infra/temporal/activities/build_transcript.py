from itertools import groupby
from operator import attrgetter
from tempfile import TemporaryDirectory

from anyio import Path
from pydantic import TypeAdapter
from temporalio import activity

from src.application.communications.dtos import (
    TextRepresentationDTO,
    TranscriptRepresentationDTO,
    TranscriptSegmentDTO,
    UpdateCommunicationDTO,
)
from src.application.transcription import RecognizedAudioChunk, build_transcript_segments
from src.domain.communications.types import RepresentationType
from src.domain.communications.vo import TranscriptSegment
from src.infra.temporal.helpers import download_to_from_s3

from .definitions import communications_client, s3_client
from .dtos import BuildTranscriptInput, BuildTranscriptResult

_transcript_segments_adapter = TypeAdapter(tuple[TranscriptSegment, ...])


def _build_transcript_representation_dto(
    segments: tuple[TranscriptSegment, ...],
) -> TranscriptRepresentationDTO:
    return TranscriptRepresentationDTO(
        type=RepresentationType.TRANSCRIPT,
        segments=[TranscriptSegmentDTO.model_validate(segment) for segment in segments],
    )


def _timestamp_to_str(ms: int) -> str:
    """Timestamp в формате `[часы]:[минуты]:[секунды]`."""
    hours, rest = divmod(ms // 1000, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def _build_text_representation_dto(
    segments: tuple[TranscriptSegment, ...],
    language: str | None = None,
) -> TextRepresentationDTO:
    """Строит текстовое представление транскрибации.

    Пример:
        [00:00:03] SPEAKER_00: Добрый день, коллеги.
        [00:00:07] SPEAKER_01: Здравствуйте.
    """

    lines: list[str] = []

    for speaker, group in groupby(segments, key=attrgetter("speaker")):
        turn = list(group)
        if not (text := " ".join(segment.text for segment in turn if segment.text)):
            continue

        started_ms = turn[0].started_ms
        timestamp = f"[{_timestamp_to_str(started_ms)}] " if started_ms is not None else ""
        lines.append(f"{timestamp}{speaker}: {text}")

    return TextRepresentationDTO(content="\n".join(lines), language=language)


@activity.defn(name="build_transcript")
async def build_transcript(input: BuildTranscriptInput) -> BuildTranscriptResult:
    """Выполняет разрешение спикеров во всех чанках и обновляет коммуникацию."""

    chunks: list[RecognizedAudioChunk] = []

    with TemporaryDirectory(prefix="build-transcript") as temp_dir:
        temp_path = Path(temp_dir)

        for ref in sorted(input.chunks, key=lambda x: x.chunk.index):
            path = temp_path / f"{ref.chunk.index:04d}.json"
            await download_to_from_s3(s3_client, ref.storage_key, path)

            payload = await path.read_bytes()
            segments = _transcript_segments_adapter.validate_json(payload)
            chunks.append(RecognizedAudioChunk(chunk=ref.chunk, segments=segments))

            activity.heartbeat("loading-transcripts", ref.chunk.index)

        # Build valid speakers transcripts
        transcript = build_transcript_segments(tuple(chunks))

        # Persist final representations
        activity.heartbeat("saving-transcript")

        transcript_representation = _build_transcript_representation_dto(transcript)
        text_representation = _build_text_representation_dto(transcript, transcript_representation.language)
        await communications_client.update_communication(
            input.communication_id,
            UpdateCommunicationDTO(representations=[transcript_representation, text_representation]),
        )

        speakers = {segment.speaker for segment in transcript if segment.speaker is not None}
        return BuildTranscriptResult(segment_count=len(transcript), speakers_count=len(speakers))


__all__ = ["build_transcript"]
