from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioChunk:
    index: int

    start_ms: int
    end_ms: int

    accepted_start_ms: int
    accepted_end_ms: int

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def accepted_duration_ms(self) -> int:
        return self.accepted_end_ms - self.accepted_start_ms


@dataclass(frozen=True, slots=True)
class AudioChunkRef(AudioChunk):
    """Ссылка на материализованный аудиочанк."""

    storage_key: str


@dataclass(frozen=True, slots=True)
class AudioChunkingOptions:
    target_duration_ms: int = 60_000
    min_duration_ms: int = 10_000
    max_duration_ms: int = 90_000

    boundary_search_ms: int = 10_000
    overlap_ms: int = 1_000
