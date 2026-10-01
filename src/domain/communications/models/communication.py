from typing import Annotated, Any

from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import UUID

from ddf.domain.models import AggregateRoot
from typing_extensions import Doc

from src.domain.communications.types import CommunicationType
from src.domain.communications.vo import CommunicationMeta, CommunicationRepresentation, Period


@dataclass(frozen=True, slots=True, kw_only=True)
class Participant:
    """Участник коммуникации."""

    display_name: str
    user_id: Annotated[UUID | None, Doc("Идентификатор пользователя в системе")] = None


@dataclass(frozen=True, slots=True)
class ExternalRef:
    """Ссылка на внешний источник."""

    id: Annotated[str, Doc("Идентификатор коммуникации у внешнего источника")]
    source: Annotated[str, Doc("Имя внешнего источника, например: 'telemost', 'telegram', ...")]


@dataclass(kw_only=True)
class Communication(AggregateRoot):
    """Коммуникация между группой лиц."""

    organization_id: UUID

    original_media_id: Annotated[UUID | None, Doc("Идентификатор исходного медиа")] = None
    external: ExternalRef | None = None

    title: str | None = None
    type: CommunicationType
    meta: CommunicationMeta
    raw_data: Mapping[str, Any] = field(default_factory=dict, repr=False)

    participants: tuple[Participant, ...]
    period: Period

    representations: list[CommunicationRepresentation] = field(default_factory=list)

    def add_representation(self, representation: CommunicationRepresentation) -> None:
        """Добавляет представление, заменяя существующее того же типа."""

        self.representations = [
            existing for existing in self.representations if existing.type != representation.type
        ]
        self.representations.append(representation)
