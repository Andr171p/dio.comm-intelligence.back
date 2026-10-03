from typing import Annotated

from collections.abc import AsyncIterator

from ddf.application.events import EventDispatcher
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database import sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_event_dispatcher(session: DBSession, request: Request) -> EventDispatcher:
    return EventDispatcher(uow=session, evnt_publisher=request.app.state.event_publisher)


Dispatch = Annotated[EventDispatcher, Depends(get_event_dispatcher)]

__all__ = ["DBSession", "Dispatch"]
