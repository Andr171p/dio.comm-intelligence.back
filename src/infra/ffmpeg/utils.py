from typing import Any

import asyncio
import json

from anyio import Path

from src.application.audio_chunking.exceptions import AudioProcessingError

from .config import ffmpeg_config, ffprobe_config
from .dtos import AudioMeta


async def probe_audio(path: Path) -> AudioMeta:
    """Получает технические характеристики аудиопотока."""

    process = await asyncio.create_subprocess_exec(
        ffprobe_config.path,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels,duration",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise AudioProcessingError(f"ffprobe failed: {stderr.decode(errors='replace')}")

    payload: dict[str, Any] = json.loads(stdout)

    streams = payload.get("streams") or []
    if not streams:
        raise AudioProcessingError("Media does not contain an audio stream")

    stream = streams[0]

    duration = stream.get("duration")
    if duration is None:
        duration = payload.get("format", {}).get("duration")

    if duration is None:
        raise AudioProcessingError("Unable to determine audio duration")

    return AudioMeta(
        duration_ms=round(float(duration) * 1000),
        sample_rate=int(stream["sample_rate"]),
        channels=int(stream["channels"]),
        codec=stream.get("codec_name"),
    )


async def prepare_audio(
    source: Path,
    destination: Path,
    *,
    channels: int = 1,
    sample_rate: int = 16_000,
) -> AudioMeta:
    """Извлекает и нормализует аудиодорожку для дальнейшей обработки."""

    await destination.parent.mkdir(parents=True, exist_ok=True)

    process = await asyncio.create_subprocess_exec(
        ffmpeg_config.path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        # Только первый audio stream.
        "-map",
        "0:a:0",
        # Без видео.
        "-vn",
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        "-c:a",
        "flac",
        "-threads",
        str(ffmpeg_config.threads),
        "-y",
        str(destination),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        _, stderr = await process.communicate()
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise

    if process.returncode != 0:
        raise AudioProcessingError(f"ffmpeg failed: {stderr.decode(errors='replace')}")

    return await probe_audio(destination)
