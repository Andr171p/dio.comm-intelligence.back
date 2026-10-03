"""MCP tools для ИИ-агента DIOS: поиск коммуникаций и чтение расшифровок.

Docstring каждого tool - это его описание для LLM.
"""

from typing import Annotated

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from src.application.communications.dtos import (
    CommunicationCardDTO,
    TranscriptMatchDTO,
    TranscriptPageDTO,
)
from src.domain.communications.types import CommunicationType
from src.infra.database import sessionmaker
from src.infra.database.communications import queries

from .auth import get_current_user
from .config import mcp_config

DateFrom = Annotated[
    datetime | None,
    Field(description="Начало периода в ISO 8601 с часовым поясом, например 2026-10-03T00:00:00+05:00"),
]
DateTo = Annotated[
    datetime | None,
    Field(description="Конец периода (не включительно) в ISO 8601 с часовым поясом"),
]


def _with_timezone(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value

    return value.replace(tzinfo=ZoneInfo(mcp_config.default_timezone))


def _page(content: str, offset: int, max_chars: int) -> tuple[str, int | None]:
    """Вырезает страницу по границе реплик (строк), чтобы не рвать реплику посередине."""

    end = offset + max_chars
    if end >= len(content):
        return content[offset:], None

    cut = content.rfind("\n", offset, end)
    if cut <= offset:  # одна реплика длиннее страницы
        return content[offset:end], end

    return content[offset:cut], cut + 1


async def find_communications(
    date_from: DateFrom = None,
    date_to: DateTo = None,
    query: Annotated[str | None, Field(description="Подстрока названия или повестки")] = None,
    participant: Annotated[str | None, Field(description="Имя участника")] = None,
    communication_type: Annotated[
        CommunicationType | None, Field(description="conference - совещания/встречи, call - звонки"),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 20,
) -> list[CommunicationCardDTO]:
    """Находит совещания и звонки организации пользователя (новые первыми).

    Используй первым шагом, чтобы получить id коммуникации. Период пересекается с временем
    проведения: для «вчера» передай начало и конец вчерашнего дня в часовом поясе пользователя.
    """

    user = get_current_user()

    async with sessionmaker() as session:
        return await queries.find_communications(
            session,
            organization_id=user.user.organization_id,
            started_from=_with_timezone(date_from),
            started_to=_with_timezone(date_to),
            query=query,
            participant=participant,
            communication_type=communication_type,
            limit=limit,
        )


async def get_communication_transcript(
    communication_id: Annotated[UUID, Field(description="id из find_communications или search_transcripts")],
    offset: Annotated[int, Field(ge=0, description="Смещение страницы (next_offset предыдущей)")] = 0,
    max_chars: Annotated[int, Field(ge=1_000, le=50_000, description="Размер страницы в символах")] = 20_000,
) -> TranscriptPageDTO:
    """Возвращает расшифровку коммуникации: реплики `[чч:мм:сс] speaker_N: текст`.

    Часовое совещание - около 60 000 символов, поэтому текст отдаётся страницами: читай,
    пока next_offset не станет null. Отвечая, ссылайся на таймкоды реплик.
    """

    user = get_current_user()

    async with sessionmaker() as session:
        cards = await queries.get_communication_cards(
            session, [communication_id], organization_id=user.user.organization_id,
        )
        if (card := cards.get(communication_id)) is None:
            raise ToolError(f"Communication {communication_id} not found.")

        content = await queries.get_transcript_text(session, communication_id)

    if content is None:
        raise ToolError(f"Transcript of communication {communication_id} is not ready yet.")

    page, next_offset = _page(content, offset, max_chars)
    return TranscriptPageDTO(
        communication=card,
        content=page,
        offset=offset,
        next_offset=next_offset,
        total_length=len(content),
    )


async def search_transcripts(
    query: Annotated[
        str, Field(min_length=2, description="Слова или фраза, синтаксис websearch: \"бюджет -отпуск\""),
    ],
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
) -> list[TranscriptMatchDTO]:
    """Полнотекстовый поиск по расшифровкам (с учётом словоформ русского языка).

    Возвращает самые релевантные коммуникации и реплики с таймкодами, где встречается запрос.
    Используй, когда неизвестно, на какой встрече обсуждали тему.
    """

    user = get_current_user()

    async with sessionmaker() as session:
        return await queries.search_transcripts(
            session,
            organization_id=user.user.organization_id,
            query=query,
            started_from=_with_timezone(date_from),
            started_to=_with_timezone(date_to),
            limit=limit,
        )


__all__ = ["find_communications", "get_communication_transcript", "search_transcripts"]
