import asyncio
from pathlib import Path

from src.application.recognizer import RecognitionOptions
from src.infra.whisper.config import WhisperConfig
from src.infra.whisper.recognizer import WhisperRecognizer

AUDIO_PATH = Path("audio_2026-10-01_16-40-31.ogg")


async def main() -> None:
    audio = AUDIO_PATH.read_bytes()  # noqa: ASYNC240

    config = WhisperConfig(base_url="http://localhost:9000", timeout=600)
    recognizer = WhisperRecognizer(config=config)

    try:
        transcript = await recognizer.recognize(
            audio,
            RecognitionOptions(
                filename=AUDIO_PATH.name,
                content_type="audio/mpeg",
                language="ru",
                diarize=True,
                min_speakers=2,
                max_speakers=2,
            ),
        )

        for segment in transcript.segments:
            print(
                f"[{segment.started_ms}–{segment.ended_ms} ms] "
                f"{segment.speaker}: {segment.text} "
                f"(confidence={segment.confidence})"
            )
    finally:
        await recognizer.close()


if __name__ == "__main__":
    asyncio.run(main())
