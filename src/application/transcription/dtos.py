from dataclasses import dataclass

from src.application.audio_chunking import AudioChunkRef
from src.domain.communications.vo import TranscriptSegment


@dataclass(frozen=True, slots=True)
class RecognizedAudioChunk:
    """распознанный аудиочанк."""

    chunk: AudioChunkRef
    segments: tuple[TranscriptSegment, ...]


@dataclass(frozen=True, slots=True)
class SpeakerResolutionOptions:
    """Настройки разрешения speaker labels между чанками."""

    min_shared_speech_ms: int = 500
    min_similarity: float = 0.5
