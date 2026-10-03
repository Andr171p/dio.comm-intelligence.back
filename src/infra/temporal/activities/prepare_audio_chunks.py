from tempfile import TemporaryDirectory

import aiofiles
from temporalio import activity

from src.application.audio_chunking import AudioChunkRef
from src.infra.temporal.helpers import build_audio_chunk_key, download_to_from_s3, materialize_audio_chunk

from .definitions import audio_config, s3_client
from .dtos import PrepareAudioChunksInput


def _get_last_completed_index() -> int:
    details = activity.info().heartbeat_details

    if not details:
        return -1

    value = details[0]

    if not isinstance(value, int):
        return -1

    return value


@activity.defn(name="prepare_audio_chunks")
async def prepare_audio_chunks(input: PrepareAudioChunksInput) -> tuple[AudioChunkRef, ...]:
    refs: list[AudioChunkRef] = []

    last_completed_index = _get_last_completed_index()

    with TemporaryDirectory(audio_config.temp_dir) as temp_dir:
        source = f"{temp_dir}/prepared.flac"
        await download_to_from_s3(s3_client, input.source.storage_key, source)

        for chunk in input.chunks:
            key = build_audio_chunk_key(chunk)
            storage_key = f"processing/{input.processing_id}/chunks/{key}.flac"

            ref = AudioChunkRef(
                index=chunk.index,
                storage_key=storage_key,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                accepted_start_ms=chunk.accepted_start_ms,
                accepted_end_ms=chunk.accepted_end_ms,
            )

            if chunk.index <= last_completed_index:
                refs.append(ref)
                continue

            async with (
                materialize_audio_chunk(source, chunk, audio_config) as path,
                aiofiles.open(str(path), mode="rb") as file,
            ):
                await s3_client.upload_stream(file, storage_key, "audio/flac")

            refs.append(ref)
            activity.heartbeat(chunk.index)

    return tuple(refs)


__all__ = ["prepare_audio_chunks"]
