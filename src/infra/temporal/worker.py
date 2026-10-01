"""Temporal воркер обработки коммуникаций: `python -m src.infra.temporal.worker`."""

import asyncio
import logging

from temporalio.worker import Worker

from . import activities
from .client import connect
from .config import TemporalConfig
from .workflows import ProcessCommunicationWorkflow

temporal_config = TemporalConfig()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    client = await connect(temporal_config)
    worker = Worker(
        client,
        task_queue=temporal_config.task_queue,
        workflows=[ProcessCommunicationWorkflow],
        activities=activities.ACTIVITIES,
        max_concurrent_activities=temporal_config.max_concurrent_activities,
    )

    try:
        await worker.run()
    finally:
        await activities.close()


if __name__ == "__main__":
    asyncio.run(main())
