from typing import ClassVar

from dataclasses import dataclass
from uuid import UUID

from ddf.domain.events import Event


@dataclass(frozen=True, kw_only=True)
class CommunicationCreated(Event):
    event_type: ClassVar[str] = "communication.created"

    communication_id: UUID


__all__ = ["CommunicationCreated"]
