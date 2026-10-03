from tempfile import TemporaryDirectory

from anyio import Path
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.infra.temporal.helpers import download_to_from_media, heartbeat_periodically

from .definitions import audio_config, communications_client, s3_client
from .dtos import CommunicationProcessingInput


@activity.defn(name="prepare_audio")
async def prepare_audio(input: CommunicationProcessingInput) -> ...:
    """Подготавливает исходное медиа к дальнейшей обработке.

    Activity:

        1. Загружает Communication и определяет исходное медиа.
        2. Скачивает media во временный локальный файл.
        3. Извлекает и нормализует аудиодорожку в FLAC.
        4. Потоково выполняет VAD.
        5. Строит логический план чанков.
        6. Загружает подготовленное аудио в processing storage.

    В Temporal возвращаются только компактные ссылки и временные
    диапазоны. Содержимое аудио через Workflow History не передаётся.

    Операция идемпотентна относительно Temporal retry, поскольку
    storage key детерминирован через ``processing_id``.
    """

    communication = await communications_client.get_communication(input.communication_id)

    if communication is None:
        raise ApplicationError(
            f"Communication with ID {input.communication_id!r} not found.",
            non_retryable=True,
        )

    if communication.original_media_id is None:
        raise ApplicationError(
            f"Communication with ID {communication.id!r} has no original media.",
            non_retryable=True,
        )

    storage_key = f"processing/{input.processing_id}/prepared/audio.flac"

    with TemporaryDirectory(dir=audio_config.temp_dir, prefix="prepare-audio-") as temp_dir:
        temp_path = Path(temp_dir)

        original_path = temp_path / "original"
        prepared_path = temp_path / "prepared.flac"

        # 1. Download original media
        async with heartbeat_periodically(detail="downloading-media"):
            await download_to_from_s3(s3_cli)
