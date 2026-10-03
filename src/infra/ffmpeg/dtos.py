from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioMeta:
    """Техническая информация об аудиопотоке."""

    duration_ms: int
    sample_rate: int
    channels: int
    codec: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedAudio:
    """Подготовленный к обработке локальный аудиофайл."""

    path: Path
    meta: AudioMeta
