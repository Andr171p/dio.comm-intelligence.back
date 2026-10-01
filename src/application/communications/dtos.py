from typing import Annotated, Literal

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, PositiveInt
from pydantic.alias_generators import to_camel

from src.domain.communications.models import ExternalRef
from src.domain.communications.types import CommunicationType
from src.domain.communications.vo import CallDirection, ConferenceFormat


class ParticipantDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    display_name: str = Field(min_length=1, description="Отображаемое имя участника")
    user_id: UUID | None = Field(default=None, description="Идентификатор пользователя в системе")


class ConferenceMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    type: Literal[CommunicationType.CONFERENCE] = CommunicationType.CONFERENCE

    format: ConferenceFormat = Field(default=ConferenceFormat.HYBRID, description="Формат проведения")
    organizer_id: UUID | None = Field(default=None, description="Идентификатор организатора")
    agenda: str | None = Field(default=None, min_length=1, max_length=255, description="Повестка дня")
    url: HttpUrl | None = Field(default=None, description="Ссылка на встречу")
    address: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Место проведения конференции",
    )


class CallMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    type: Literal[CommunicationType.CALL] = CommunicationType.CALL

    src: str = Field(description="Номер телефона вызывающего")
    dst: str = Field(description="Номер телефона вызываемого")
    direction: CallDirection = Field(description="Направление звонка (входящий/исходящий)")
    bill_sec: PositiveInt = Field(description="Длительность без гудков")


CommunicationMeta = Annotated[CallMeta | ConferenceMeta, Field(discriminator="type")]


class CreateCommunicationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    class _Period(BaseModel):
        started_at: AwareDatetime = Field(description="Дата и время начала")
        ended_at: AwareDatetime = Field(description="Дата и время завершения")

    external: ExternalRef | None = Field(default=None, description="Ссылка на внешний источник")
    original_media_id: UUID = Field(description="Идентификатор исходного файла")
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Название/заголовок коммуникации",
    )
    meta: CommunicationMeta = Field(description="Метаинформация")
    participants: list[ParticipantDTO] = Field(default_factory=list, description="Список участников")
    period: _Period = Field(description="Временной промежуток")


class UpdateCommunicationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Название/заголовок коммуникации",
    )
    representations: ...


class CommunicationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


__all__ = [
    "CommunicationResponse",
    "CreateCommunicationDTO",
    "UpdateCommunicationDTO",
]
