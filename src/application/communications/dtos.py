from typing import Annotated, Literal

from datetime import datetime
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    NonNegativeInt,
    PositiveInt,
)
from pydantic.alias_generators import to_camel

from src.domain.communications.models import ExternalRef
from src.domain.communications.types import CommunicationType, RepresentationType
from src.domain.communications.vo import (
    CallDirection,
    CallMeta,
    ChatRepresentation,
    ConferenceFormat,
    ConferenceMeta,
    Message,
    TextRepresentation,
    TranscriptRepresentation,
    TranscriptSegment,
)


class _BaseDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, from_attributes=True)


class ParticipantDTO(_BaseDTO):
    display_name: str = Field(min_length=1, description="Отображаемое имя участника")
    user_id: UUID | None = Field(default=None, description="Идентификатор пользователя в системе")


class PeriodDTO(_BaseDTO):
    started_at: AwareDatetime = Field(description="Дата и время начала")
    ended_at: AwareDatetime = Field(description="Дата и время завершения")


# ===========================================================================================================
# Meta
# ===========================================================================================================


class ConferenceMetaDTO(_BaseDTO):
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

    def to_domain(self) -> ConferenceMeta:
        return ConferenceMeta(
            format=self.format,
            organizer_id=self.organizer_id,
            agenda=self.agenda,
            url=str(self.url) if self.url is not None else None,
            address=self.address,
        )


class CallMetaDTO(_BaseDTO):
    type: Literal[CommunicationType.CALL] = CommunicationType.CALL

    src: str = Field(description="Номер телефона вызывающего")
    dst: str = Field(description="Номер телефона вызываемого")
    direction: CallDirection = Field(description="Направление звонка (входящий/исходящий)")
    bill_sec: PositiveInt = Field(description="Длительность без гудков")

    def to_domain(self) -> CallMeta:
        return CallMeta(src=self.src, dst=self.dst, direction=self.direction, bill_sec=self.bill_sec)


CommunicationMetaDTO = Annotated[CallMetaDTO | ConferenceMetaDTO, Field(discriminator="type")]

# ===========================================================================================================
# Representations
# ===========================================================================================================


class TranscriptSegmentDTO(_BaseDTO):
    id: str = Field(description="Идентификатор сегмента")
    speaker: str = Field(description="Метка спикера")
    text: str = Field(description="Распознанный текст")
    started_ms: NonNegativeInt | None = Field(default=None, description="Начало от начала записи, мс")
    ended_ms: NonNegativeInt | None = Field(default=None, description="Конец от начала записи, мс")
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Уверенность модели распознавания",
    )


class TranscriptRepresentationDTO(_BaseDTO):
    type: Literal[RepresentationType.TRANSCRIPT] = RepresentationType.TRANSCRIPT

    segments: list[TranscriptSegmentDTO] = Field(description="Распознанные сегменты")
    language: str | None = Field(default=None, description="Язык записи")

    def to_domain(self) -> TranscriptRepresentation:
        return TranscriptRepresentation(
            segments=tuple(TranscriptSegment(**segment.model_dump()) for segment in self.segments),
            language=self.language,
        )


class MessageDTO(_BaseDTO):
    id: str = Field(description="Идентификатор сообщения")
    created_at: AwareDatetime = Field(description="Дата и время отправки")
    text: str | None = Field(default=None, description="Текст сообщения")
    attachments: list[UUID] = Field(default_factory=list, description="Вложения")
    reply_to_id: str | None = Field(default=None, description="Ответ на сообщение")
    thread_id: str | None = Field(default=None, description="Тред")


class ChatRepresentationDTO(_BaseDTO):
    type: Literal[RepresentationType.CHAT] = RepresentationType.CHAT

    messages: list[MessageDTO] = Field(description="Сообщения чата")

    def to_domain(self) -> ChatRepresentation:
        return ChatRepresentation(
            messages=tuple(
                Message(**message.model_dump(exclude={"attachments"}), attachments=tuple(message.attachments))
                for message in self.messages
            ),
        )


class TextRepresentationDTO(_BaseDTO):
    type: Literal[RepresentationType.TEXT] = RepresentationType.TEXT

    content: str = Field(description="Сплошной текст коммуникации")
    language: str | None = Field(default=None, description="Язык текста")

    def to_domain(self) -> TextRepresentation:
        return TextRepresentation(content=self.content, language=self.language)


RepresentationDTO = Annotated[
    TranscriptRepresentationDTO | ChatRepresentationDTO | TextRepresentationDTO,
    Field(discriminator="type"),
]

# ===========================================================================================================
# Commands & responses
# ===========================================================================================================


class CreateCommunicationDTO(_BaseDTO):
    external: ExternalRef | None = Field(default=None, description="Ссылка на внешний источник")
    original_media_id: UUID = Field(description="Идентификатор исходного файла")
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Название/заголовок коммуникации",
    )
    meta: CommunicationMetaDTO = Field(description="Метаинформация")
    participants: list[ParticipantDTO] = Field(default_factory=list, description="Список участников")
    period: PeriodDTO = Field(description="Временной промежуток")


class UpdateCommunicationDTO(_BaseDTO):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Название/заголовок коммуникации",
    )
    representations: list[RepresentationDTO] = Field(
        default_factory=list,
        description="Представления коммуникации (заменяют существующие того же типа)",
    )


class CommunicationResponse(_BaseDTO):
    id: UUID
    organization_id: UUID
    original_media_id: UUID | None
    external: ExternalRef | None
    title: str | None
    type: CommunicationType
    meta: CommunicationMetaDTO
    participants: list[ParticipantDTO]
    period: PeriodDTO
    representations: list[RepresentationDTO]
    created_at: datetime
    updated_at: datetime


# ===========================================================================================================
# Search (read models для поиска и MCP)
# ===========================================================================================================


class CommunicationCardDTO(_BaseDTO):
    """Компактная карточка коммуникации без представлений."""

    id: UUID
    title: str | None
    type: CommunicationType
    agenda: str | None = Field(default=None, description="Повестка (для конференций)")
    participants: list[str] = Field(description="Отображаемые имена участников")
    started_at: datetime
    ended_at: datetime
    has_transcript: bool = Field(description="Готова ли расшифровка")


class TranscriptPageDTO(_BaseDTO):
    """Страница LLM-ready расшифровки (длинные встречи читаются по частям)."""

    communication: CommunicationCardDTO
    content: str = Field(description="Реплики в формате `[чч:мм:сс] speaker_N: текст`")
    offset: int = Field(description="Смещение страницы в символах")
    next_offset: int | None = Field(description="Смещение следующей страницы, null - расшифровка прочитана")
    total_length: int = Field(description="Полная длина расшифровки в символах")


class TranscriptMatchDTO(_BaseDTO):
    """Коммуникация, в расшифровке которой найден запрос."""

    communication: CommunicationCardDTO
    fragments: list[str] = Field(description="Реплики с таймкодами, содержащие запрос")


__all__ = [
    "CallMetaDTO",
    "ChatRepresentationDTO",
    "CommunicationCardDTO",
    "CommunicationResponse",
    "ConferenceMetaDTO",
    "CreateCommunicationDTO",
    "RepresentationDTO",
    "TextRepresentationDTO",
    "TranscriptMatchDTO",
    "TranscriptPageDTO",
    "TranscriptRepresentationDTO",
    "TranscriptSegmentDTO",
    "UpdateCommunicationDTO",
]
