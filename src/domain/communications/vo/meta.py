from typing import Annotated

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from typing_extensions import Doc


class ConferenceFormat(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    HYBRID = "hybrid"


class CallDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ConferenceMeta:
    """Метаинформация конференции (длительные коммуникации)."""

    format: ConferenceFormat
    organizer_id: Annotated[UUID | None, Doc("Идентификатор пользователя организатора")] = None
    agenda: Annotated[str | None, Doc("Повестка дня")] = None
    url: Annotated[str | None, Doc("Ссылка на конференцию")] = None
    address: Annotated[str | None, Doc("Место проведения")] = None


@dataclass(frozen=True, slots=True)
class CallMeta:
    """Метаинформация звонка."""

    src: str
    dst: str
    direction: CallDirection
    bill_sec: int


type CommunicationMeta = ConferenceMeta | CallMeta

__all__ = [
    "CallDirection",
    "CallMeta",
    "CommunicationMeta",
    "ConferenceFormat",
    "ConferenceMeta",
]
