from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.application.transcription import ChunkTranscript

    from .activities import cleanup_audio, get_communication, prepare_audio, save_transcript, transcribe_chunk
    from .dtos import (
        PROCESS_COMMUNICATION_WORKFLOW,
        PrepareAudioParams,
        SaveTranscriptParams,
        TranscribeChunkParams,
    )

_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=5,
)

# Долгие activities (ffmpeg, распознавание) шлют heartbeat - зависший воркер обнаруживается за минуту
_AUDIO_TIMEOUT = timedelta(hours=1)
_HEARTBEAT_TIMEOUT = timedelta(minutes=1)


@workflow.defn(name=PROCESS_COMMUNICATION_WORKFLOW)
class ProcessCommunicationWorkflow:
    """Подготовка коммуникации к анализу."""

    @workflow.run
    async def run(self, communication_id: UUID) -> None:
        communication = await workflow.execute_activity(
            get_communication,
            communication_id,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=_RETRY_POLICY,
        )

        if communication.original_media_id is not None:
            await self._transcribe(communication_id, communication.original_media_id)

    async def _transcribe(self, communication_id: UUID, media_id: UUID) -> None:
        """Транскрибирует запись по фрагментам.

        Язык определяется по первому фрагменту и фиксируется для остальных,
        чтобы распознавание не "перескакивало" между языками.
        """

        audio = await workflow.execute_activity(
            prepare_audio,
            PrepareAudioParams(communication_id, media_id),
            start_to_close_timeout=_AUDIO_TIMEOUT,
            heartbeat_timeout=_HEARTBEAT_TIMEOUT,
            retry_policy=_RETRY_POLICY,
        )

        try:
            language: str | None = None
            transcripts: list[ChunkTranscript] = []

            for file in audio.chunks:
                transcript = await workflow.execute_activity(
                    transcribe_chunk,
                    TranscribeChunkParams(file, language),
                    start_to_close_timeout=_AUDIO_TIMEOUT,
                    heartbeat_timeout=_HEARTBEAT_TIMEOUT,
                    retry_policy=_RETRY_POLICY,
                )
                language = language or transcript.transcript.language
                transcripts.append(transcript)

            await workflow.execute_activity(
                save_transcript,
                SaveTranscriptParams(communication_id, tuple(transcripts)),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_RETRY_POLICY,
            )
        finally:
            await workflow.execute_activity(
                cleanup_audio, communication_id, start_to_close_timeout=timedelta(minutes=1),
            )
