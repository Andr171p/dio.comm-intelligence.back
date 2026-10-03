from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from ddf.application.crud import Crud
from ddf.application.exceptions import NotFoundError

from src.domain.communications.events import CommunicationCreated
from src.domain.communications.models import Communication, Participant
from src.domain.communications.vo import CallMeta, ConferenceMeta, Period

from .dtos import (
    CallMetaDTO,
    CommunicationResponse,
    ConferenceMetaDTO,
    CreateCommunicationDTO,
    UpdateCommunicationDTO,
)

# ===========================================================================================================
# Options
# ===========================================================================================================


@dataclass(frozen=True, slots=True)
class CreateCommunicationOptions:
    organization_id: UUID


@dataclass(frozen=True, slots=True)
class ReadCommunicationOptions:
    organization_id: UUID


CommunicationCrud = Crud[
    Communication,
    CommunicationResponse,
    CreateCommunicationDTO,
    UpdateCommunicationDTO,
    CreateCommunicationOptions,
    ReadCommunicationOptions,
    None,
    None,
]

# ===========================================================================================================
# Handlers
# ===========================================================================================================


async def create_handler(
    dto: CreateCommunicationDTO, options: CreateCommunicationOptions | None = None,
) -> Communication:
    if options is None:
        raise ValueError("Organization is required to create a communication.")

    communication = Communication(
        organization_id=options.organization_id,
        original_media_id=dto.original_media_id,
        external=dto.external,
        title=dto.title,
        type=dto.meta.type,
        meta=dto.meta.to_domain(),
        participants=tuple(
            Participant(display_name=participant_dto.display_name, user_id=participant_dto.user_id)
            for participant_dto in dto.participants
        ),
        period=Period(started_at=dto.period.started_at, ended_at=dto.period.ended_at),
    )
    communication.register_event(CommunicationCreated(communication_id=communication.id))
    return communication


async def update_handler(
    communication: Communication, dto: UpdateCommunicationDTO, options: None = None,
) -> Communication:
    if dto.title is not None:
        communication.title = dto.title

    for representation in dto.representations:
        communication.add_representation(representation.to_domain())

    return communication

# ===========================================================================================================
# Wrappers
# ===========================================================================================================


async def read_wrapper(
    read: Callable[[Communication, ReadCommunicationOptions | None], Awaitable[Communication]],
    communication: Communication,
    options: ReadCommunicationOptions | None = None,
) -> Communication:
    """Скрывает коммуникации чужой организации (без options - сервисный доступ)."""

    if options is not None and communication.organization_id != options.organization_id:
        raise NotFoundError(f"Communication with ID {communication.id} not found.")

    return await read(communication, options)

# ===========================================================================================================
# Mapping
# ===========================================================================================================


def to_response(communication: Communication) -> CommunicationResponse:
    match communication.meta:
        case CallMeta():
            meta: CallMetaDTO | ConferenceMetaDTO = CallMetaDTO.model_validate(communication.meta)
        case ConferenceMeta():
            meta = ConferenceMetaDTO.model_validate(communication.meta)
        case _:
            raise TypeError(f"Unsupported communication meta: {type(communication.meta).__name__}")

    return CommunicationResponse(
        id=communication.id,
        organization_id=communication.organization_id,
        original_media_id=communication.original_media_id,
        external=communication.external,
        title=communication.title,
        type=communication.type,
        meta=meta,
        participants=communication.participants,  # type: ignore[arg-type]
        period=communication.period,  # type: ignore[arg-type]
        representations=communication.representations,  # type: ignore[arg-type]
        created_at=communication.created_at,
        updated_at=communication.updated_at,
    )


__all__ = [
    "CommunicationCrud",
    "CreateCommunicationOptions",
    "ReadCommunicationOptions",
    "create_handler",
    "read_wrapper",
    "to_response",
    "update_handler",
]
