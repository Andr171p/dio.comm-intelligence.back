from typing import Annotated

from dataclasses import dataclass

from ddf.application.crud import Crud
from fastapi import Depends

from src.domain.communications.models import Communication, Participant
from src.domain.communications.vo import Period

from .dtos import CommunicationResponse, CreateCommunicationDTO, UpdateCommunicationDTO

CommunicationCrud = Crud[
    Communication,
    CommunicationResponse,
    CreateCommunicationDTO,
    UpdateCommunicationDTO,
    None,
    None,
    None,
    None,
]

# ===========================================================================================================
# Handlers
# ===========================================================================================================


@dataclass(frozen=True, slots=True)
class CreateCommunicationOptions:
    ...

# ===========================================================================================================
# Handlers
# ===========================================================================================================


async def create_handler(dto: CreateCommunicationDTO, options: object | None = None) -> Communication:
    return Communication(
        organization_id=...,
        original_media_id=dto.original_media_id,
        external=dto.external,
        title=dto.title,
        type=dto.meta.type,
        meta=...,
        participants=tuple(
            Participant(display_name=participant_dto.display_name, user_id=participant_dto.user_id)
            for participant_dto in dto.participants
        ),
        period=Period(started_at=dto.period.started_at, ended_at=dto.period.ended_at),
    )

# ===========================================================================================================
# Wrappers
# ===========================================================================================================


# ===========================================================================================================
# Dependencies
# ===========================================================================================================


def get_communication_crud(
    dispatcher: ...,
    repository: ...,
) -> CommunicationCrud:
    return CommunicationCrud(
        repository=repository,
        dispatcher=dispatcher,
        to_response=...,
        create_handler=create_handler,
    )


CommunicationCrudDep = Annotated[CommunicationCrud, Depends(get_communication_crud)]


__all__ = ["CommunicationCrudDep"]
