import asyncio
from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.application.recognizer import RecognitionOptions

    from .activities import (
        build_transcript,
        cleanup_processing_artifacts,
        prepare_audio_chunks,
        prepare_communication,
        recognize_audio_chunk,
    )
    from .activities.dtos import (
        BuildTranscriptInput,
        CommunicationProcessingInput,
        PrepareAudioChunksInput,
        RecognizeAudioChunkInput,
    )
    from .dtos import PROCESS_COMMUNICATION_WORKFLOW

_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=5,
)

# Долгие activities (ffmpeg, VAD, распознавание) шлют heartbeat - зависший воркер обнаруживается за минуту
_AUDIO_TIMEOUT = timedelta(hours=1)
_HEARTBEAT_TIMEOUT = timedelta(minutes=1)


@workflow.defn(name=PROCESS_COMMUNICATION_WORKFLOW)
class ProcessCommunicationWorkflow:
    """Подготовка коммуникации к анализу (см. схему в ``src.infra.temporal``)."""

    @workflow.run
    async def run(self, communication_id: UUID) -> None:
        # Детерминирован при replay: все storage keys пайплайна строятся от него
        processing_id = workflow.uuid4()

        try:
            await self._transcribe(communication_id, processing_id)
        finally:
            await workflow.execute_activity(
                cleanup_processing_artifacts,
                processing_id,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_POLICY,
            )

    async def _transcribe(self, communication_id: UUID, processing_id: UUID) -> None:
        preparation = await workflow.execute_activity(
            prepare_communication,
            CommunicationProcessingInput(communication_id=communication_id, processing_id=processing_id),
            start_to_close_timeout=_AUDIO_TIMEOUT,
            heartbeat_timeout=_HEARTBEAT_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )

        chunks = await workflow.execute_activity(
            prepare_audio_chunks,
            PrepareAudioChunksInput(
                processing_id=processing_id,
                source=preparation.audio,
                chunks=preparation.chunks,
            ),
            start_to_close_timeout=_AUDIO_TIMEOUT,
            heartbeat_timeout=_HEARTBEAT_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )

        # Параллелизм ограничивается max_concurrent_activities воркера
        recognized = await asyncio.gather(*(
            workflow.execute_activity(
                recognize_audio_chunk,
                RecognizeAudioChunkInput(
                    communication_id=communication_id,
                    processing_id=processing_id,
                    chunk=chunk,
                    options=RecognitionOptions(filename=f"{chunk.index:04d}.flac", content_type="audio/flac"),
                ),
                start_to_close_timeout=_AUDIO_TIMEOUT,
                heartbeat_timeout=_HEARTBEAT_TIMEOUT,
                retry_policy=_RETRY_POLICY,
            )
            for chunk in chunks
        ))

        await workflow.execute_activity(
            build_transcript,
            BuildTranscriptInput(
                communication_id=communication_id,
                processing_id=processing_id,
                chunks=tuple(recognized),
            ),
            start_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=_HEARTBEAT_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )
