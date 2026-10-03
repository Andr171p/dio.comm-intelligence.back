import asyncio

from anyio import Path

from src.application.audio_chunking import AudioChunk
from src.application.audio_chunking.exceptions import AudioProcessingError

from .config import ffmpeg_config


async def extract_audio_chunk(source: Path, destination: Path, chunk: AudioChunk) -> None:
    """Извлекает один временной диапазон аудио в отдельный FLAC-файл."""

    if not await source.is_file():
        raise AudioProcessingError(f"Audio source does not exist: {source}")

    await destination.parent.mkdir(parents=True, exist_ok=True)

    start_sec = chunk.start_ms / 1000
    duration_sec = chunk.duration_ms / 1000

    process = await asyncio.create_subprocess_exec(
        ffmpeg_config.path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",

        # Input seeking.
        # Поскольку ниже выполняется transcoding, FFmpeg делает
        # accurate seek и отбрасывает данные до точной позиции.
        "-ss",
        f"{start_sec:.3f}",

        "-i",
        str(source),

        "-t",
        f"{duration_sec:.3f}",

        # Только первый audio stream.
        "-map",
        "0:a:0",

        "-vn",
        "-sn",
        "-dn",

        # FLAC заместо WAV.
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
        await destination.unlink(missing_ok=True)

        raise AudioProcessingError(
            f"Failed to extract audio chunk {chunk.index}: {stderr.decode(errors='replace')}",
        )
