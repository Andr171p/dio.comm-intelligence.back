from dataclasses import replace
from tempfile import TemporaryDirectory

from anyio import Path
from pydantic import TypeAdapter
from temporalio import activity

from src.application.audio_chunking import AudioChunkRef
from src.domain.communications.vo import TranscriptSegment
from src.infra.temporal.helpers import build_audio_chunk_key, download_to_from_s3, heartbeat_periodically

from .definitions import s3_client, speech_recognizer
from .dtos import RecognizeAudioChunkInput, RecognizedAudioChunkRef

_transcript_segments_adepter = TypeAdapter(tuple[TranscriptSegment, ...])


def _normalize_chunk_segments(
    segments: tuple[TranscriptSegment, ...],
    chunk: AudioChunkRef,
) -> tuple[TranscriptSegment, ...]:
    """Переводит локальные timestamps чанка в timestamps коммуникации.

    Сегменты из overlap принимаются только тогда, когда midpoint
    попадает в accepted range текущего чанка.
    """

    return tuple(
        replace(
            segment,
            started_ms=(chunk.start_ms + segment.started_ms if segment.started_ms is not None else None),
            ended_ms=(chunk.start_ms + segment.ended_ms if segment.ended_ms is not None else None),
        )
        for segment in segments
    )


@activity.defn(name="recognize_audio_chunk")
async def recognize_audio_chunk(input: RecognizeAudioChunkInput) -> RecognizedAudioChunkRef:
    """Распознаёт один аудиочанк и сохраняет чистый транскрипт."""

    chunk = input.chunk
    transcript_key = f"processing/{input.processing_id}/transcripts/{build_audio_chunk_key(chunk)}.json"

    with TemporaryDirectory(prefix="transcribe-audio-chunk-") as temp_dir:
        audio_path = Path(temp_dir) / f"{build_audio_chunk_key(chunk)}.flac"
        await download_to_from_s3(s3_client, chunk.storage_key, audio_path)

        activity.heartbeat("downloaded")

        async with heartbeat_periodically(detail="recognizing"):
            segments = await speech_recognizer.recognize(audio_path, input.options)

        activity.heartbeat("recognized")

        normalized_segments = _normalize_chunk_segments(segments, chunk)
        payload = _transcript_segments_adepter.dump_json(normalized_segments, by_alias=True)

        await s3_client.upload(payload, transcript_key, "application/json")

    return RecognizedAudioChunkRef(
        chunk=chunk,
        storage_key=transcript_key,
        segment_count=len(normalized_segments),
    )


__all__ = ["recognize_audio_chunk"]
