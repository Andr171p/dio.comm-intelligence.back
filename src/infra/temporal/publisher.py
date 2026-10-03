from collections.abc import Sequence
from contextlib import suppress

from ddf.application.events import EventPublisher
from ddf.domain.events import Event
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.domain.communications.events import CommunicationCreated

from .dtos import PROCESS_COMMUNICATION_WORKFLOW, process_communication_workflow_id


def create_temporal_publisher(client: Client, task_queue: str) -> EventPublisher:
    """
    Публикует доменные события как запуски workflow.

    Workflow ID детерминирован от сущности,
    поэтому повторная публикация (retries, outbox) не создаёт дублей.
    """

    async def _publish(events: Sequence[Event]) -> None:
        for event in events:
            match event:
                case CommunicationCreated(communication_id=communication_id):
                    with suppress(WorkflowAlreadyStartedError):
                        await client.start_workflow(
                            PROCESS_COMMUNICATION_WORKFLOW,
                            communication_id,
                            id=process_communication_workflow_id(communication_id),
                            task_queue=task_queue,
                            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
                        )

    return _publish


__all__ = ["create_temporal_publisher"]
