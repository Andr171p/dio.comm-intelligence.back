from .silero_vad import SileroVad

__all__ = ["get_silero_vad"]

_vad: SileroVad | None = None


def get_silero_vad() -> SileroVad:
    global _vad  # noqa: PLW0603

    if _vad is None:
        from .config import VadConfig

        config = VadConfig()  # type: ignore
        _vad = SileroVad(config)

    return _vad
