"""Контракты workflow и activities (общие для API и воркера)."""

from dataclasses import dataclass
from uuid import UUID

from src.application.transcription import AudioChunk, ChunkTranscript

PROCESS_COMMUNICATION_WORKFLOW = "process-communication"


def process_communication_workflow_id(communication_id: UUID) -> str:
    return f"communication-{communication_id}"


@dataclass(frozen=True, slots=True)
class PrepareAudioParams:
    communication_id: UUID
    media_id: UUID


@dataclass(frozen=True, slots=True)
class AudioChunkFile:
    chunk: AudioChunk
    path: str


@dataclass(frozen=True, slots=True)
class PreparedAudio:
    duration_ms: int
    chunks: tuple[AudioChunkFile, ...]


@dataclass(frozen=True, slots=True)
class TranscribeChunkParams:
    file: AudioChunkFile
    language: str | None = None


@dataclass(frozen=True, slots=True)
class SaveTranscriptParams:
    communication_id: UUID
    transcripts: tuple[ChunkTranscript, ...]
