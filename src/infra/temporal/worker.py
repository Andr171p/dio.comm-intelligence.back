import asyncio
import logging

from temporalio.worker import Worker

from .activities import (
    build_transcript,
    cleanup_processing_artifacts,
    prepare_audio_chunks,
    prepare_communication,
    recognize_audio_chunk,
)
from .activities.definitions import communications_client, media_client, speech_recognizer
from .client import connect
from .config import TemporalConfig
from .workflows import ProcessCommunicationWorkflow

temporal_config = TemporalConfig()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    client = await connect(temporal_config)
    worker = Worker(
        client,
        task_queue=temporal_config.task_queue,
        workflows=[ProcessCommunicationWorkflow],
        activities=[
            prepare_communication,
            prepare_audio_chunks,
            recognize_audio_chunk,
            build_transcript,
            cleanup_processing_artifacts,
        ],
        max_concurrent_activities=temporal_config.max_concurrent_activities,
    )

    try:
        await worker.run()
    finally:
        await asyncio.gather(communications_client.close(), media_client.close(), speech_recognizer.close())


if __name__ == "__main__":
    asyncio.run(main())
