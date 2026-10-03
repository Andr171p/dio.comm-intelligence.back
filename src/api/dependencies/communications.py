from typing import Annotated

from fastapi import Depends

from src.application.communications.crud import (
    CommunicationCrud,
    create_handler,
    read_wrapper,
    to_response,
    update_handler,
)
from src.application.repositories import CommunicationRepository
from src.infra.database.communications import SqlAlchemyCommunicationRepository

from .database import DBSession, Dispatch


def get_communication_repository(db: DBSession) -> CommunicationRepository:
    return SqlAlchemyCommunicationRepository(db)


CommunicationRepositoryDep = Annotated[CommunicationRepository, Depends(get_communication_repository)]


def get_communication_crud(
    repository: CommunicationRepositoryDep,
    dispatch: Dispatch,
) -> CommunicationCrud:
    return CommunicationCrud(
        repository=repository,
        dispatcher=dispatch,
        to_response=to_response,
        create_handler=create_handler,
        update_handler=update_handler,
        read_wrapper=read_wrapper,
    )


CommunicationCrudDep = Annotated[CommunicationCrud, Depends(get_communication_crud)]

__all__ = ["CommunicationCrudDep"]
