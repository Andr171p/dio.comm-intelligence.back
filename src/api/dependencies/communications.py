from typing import Annotated

from fastapi import Depends

from src.application.communications.crud import (
    CommunicationCrud,
    create_handler,
    read_wrapper,
    to_response,
    update_handler,
)
from src.infra.database.communications import SqlAlchemyCommunicationRepository

from .database import EventDispatcherDep, SessionDep


def get_communication_crud(session: SessionDep, dispatcher: EventDispatcherDep) -> CommunicationCrud:
    return CommunicationCrud(
        repository=SqlAlchemyCommunicationRepository(session),
        dispatcher=dispatcher,
        to_response=to_response,
        create_handler=create_handler,
        update_handler=update_handler,
        read_wrapper=read_wrapper,
    )


CommunicationCrudDep = Annotated[CommunicationCrud, Depends(get_communication_crud)]

__all__ = ["CommunicationCrudDep"]
