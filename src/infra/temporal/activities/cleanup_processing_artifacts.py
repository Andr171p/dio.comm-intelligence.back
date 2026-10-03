from uuid import UUID

from temporalio import activity

from .definitions import s3_client


@activity.defn(name="cleanup_processing_artifacts")
async def cleanup_processing_artifacts(processing_id: UUID) -> None:
    prefix = f"processing/{processing_id}/"
    await s3_client.delete_by_prefix(prefix)


__all__ = ["cleanup_processing_artifacts"]
