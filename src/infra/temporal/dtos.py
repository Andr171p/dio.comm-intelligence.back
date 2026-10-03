from uuid import UUID

PROCESS_COMMUNICATION_WORKFLOW = "process-communication"


def process_communication_workflow_id(communication_id: UUID) -> str:
    return f"communication-{communication_id}"
