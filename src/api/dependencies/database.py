from typing import Annotated

from collections.abc import AsyncIterator

from ddf.application.events import EventDispatcher
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database import session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_event_dispatcher(session: SessionDep, request: Request) -> EventDispatcher:
    """AsyncSession сама реализует протокол UnitOfWork, события публикуются после коммита."""

    return EventDispatcher(uow=session, evnt_publisher=request.app.state.event_publisher)


EventDispatcherDep = Annotated[EventDispatcher, Depends(get_event_dispatcher)]

__all__ = ["EventDispatcherDep", "SessionDep"]
