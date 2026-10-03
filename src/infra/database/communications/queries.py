"""Read-запросы поиска коммуникаций (без загрузки тяжёлых представлений)."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Text, cast, desc, exists, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from src.application.communications.dtos import CommunicationCardDTO, TranscriptMatchDTO
from src.domain.communications.types import CommunicationType, RepresentationType

from .models import FTS_CONFIG, CommunicationOrm, CommunicationRepresentationOrm

_HEADLINE_OPTIONS = "MaxWords=35, MinWords=15, MaxFragments=2, FragmentDelimiter=' … ', StartSel=«, StopSel=»"

_has_transcript = (
    exists()
    .where(
        CommunicationRepresentationOrm.communication_id == CommunicationOrm.id,
        CommunicationRepresentationOrm.type == RepresentationType.TEXT,
    )
    .label("has_transcript")
)


def _period_filters(
    organization_id: UUID,
    started_from: datetime | None,
    started_to: datetime | None,
) -> list[ColumnElement[bool]]:
    """Коммуникации организации, пересекающиеся с периодом ``[started_from, started_to)``."""

    filters = [CommunicationOrm.organization_id == organization_id, CommunicationOrm.deleted_at.is_(None)]

    if started_from is not None:
        filters.append(CommunicationOrm.ended_at >= started_from)

    if started_to is not None:
        filters.append(CommunicationOrm.started_at < started_to)

    return filters


def _to_card(model: CommunicationOrm, has_transcript: bool) -> CommunicationCardDTO:
    return CommunicationCardDTO(
        id=model.id,
        title=model.title,
        type=CommunicationType(model.type),
        agenda=model.meta.get("agenda"),
        participants=[participant["display_name"] for participant in model.participants],
        started_at=model.started_at,
        ended_at=model.ended_at,
        has_transcript=has_transcript,
    )


async def find_communications(
    session: AsyncSession,
    *,
    organization_id: UUID,
    started_from: datetime | None = None,
    started_to: datetime | None = None,
    query: str | None = None,
    participant: str | None = None,
    communication_type: CommunicationType | None = None,
    limit: int = 20,
) -> list[CommunicationCardDTO]:
    """Ищет коммуникации по периоду, названию/повестке, участнику и типу (новые первыми)."""

    filters = _period_filters(organization_id, started_from, started_to)

    if query:
        pattern = f"%{query}%"
        filters.append(
            or_(CommunicationOrm.title.ilike(pattern), CommunicationOrm.meta["agenda"].astext.ilike(pattern)),
        )

    if participant:
        filters.append(cast(CommunicationOrm.participants, Text).ilike(f"%{participant}%"))

    if communication_type is not None:
        filters.append(CommunicationOrm.type == communication_type)

    stmt = (
        select(CommunicationOrm, _has_transcript)
        .options(noload(CommunicationOrm.representations))
        .where(*filters)
        .order_by(CommunicationOrm.started_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [_to_card(model, has_transcript) for model, has_transcript in result.all()]


async def get_communication_cards(
    session: AsyncSession,
    ids: Sequence[UUID],
    *,
    organization_id: UUID,
) -> dict[UUID, CommunicationCardDTO]:
    stmt = (
        select(CommunicationOrm, _has_transcript)
        .options(noload(CommunicationOrm.representations))
        .where(CommunicationOrm.id.in_(ids), *_period_filters(organization_id, None, None))
    )
    result = await session.execute(stmt)
    return {model.id: _to_card(model, has_transcript) for model, has_transcript in result.all()}


async def get_transcript_text(session: AsyncSession, communication_id: UUID) -> str | None:
    stmt = select(CommunicationRepresentationOrm.payload["content"].astext).where(
        CommunicationRepresentationOrm.communication_id == communication_id,
        CommunicationRepresentationOrm.type == RepresentationType.TEXT,
    )
    return await session.scalar(stmt)


async def search_transcripts(
    session: AsyncSession,
    *,
    organization_id: UUID,
    query: str,
    started_from: datetime | None = None,
    started_to: datetime | None = None,
    limit: int = 5,
    fragments_limit: int = 5,
) -> list[TranscriptMatchDTO]:
    """Полнотекстовый поиск по расшифровкам.

    Сначала по GIN-индексу отбираются самые релевантные расшифровки, затем внутри них
    выбираются реплики (строки текстового представления с таймкодами), содержащие запрос.
    """

    tsquery = func.websearch_to_tsquery(FTS_CONFIG, query)

    matched = (
        select(
            CommunicationRepresentationOrm.communication_id.label("id"),
            func.ts_rank(CommunicationRepresentationOrm.search_vector, tsquery).label("rank"),
            CommunicationRepresentationOrm.payload["content"].astext.label("content"),
        )
        .join(CommunicationOrm, CommunicationOrm.id == CommunicationRepresentationOrm.communication_id)
        .where(
            CommunicationRepresentationOrm.type == RepresentationType.TEXT,
            CommunicationRepresentationOrm.search_vector.op("@@")(tsquery),
            *_period_filters(organization_id, started_from, started_to),
        )
        .order_by(desc("rank"))
        .limit(limit)
        .cte("matched")
    )
    # AS lines(line): без явного имени колонки Postgres трактует lines.line как тип line
    lines = (
        func.regexp_split_to_table(matched.c.content, "\n")
        .table_valued("line")
        .render_derived(name="lines")
        .lateral()
    )

    # Реплика может быть длинной: отдаём "[чч:мм:сс] speaker_N:" + выдержку вокруг совпадения
    speaker_prefix = func.substring(lines.c.line, r"^\[[^]]*\] [^:]*:")
    headline = func.ts_headline(FTS_CONFIG, lines.c.line, tsquery, _HEADLINE_OPTIONS)

    stmt = (
        select(matched.c.id, speaker_prefix, headline)
        .select_from(matched.join(lines, true()))
        .where(func.to_tsvector(FTS_CONFIG, lines.c.line).op("@@")(tsquery))
        .order_by(desc(matched.c.rank))
    )
    result = await session.execute(stmt)

    fragments: dict[UUID, list[str]] = {}
    for communication_id, prefix, excerpt in result.all():
        fragments.setdefault(communication_id, []).append(f"{prefix} {excerpt}" if prefix else excerpt)

    cards = await get_communication_cards(session, list(fragments), organization_id=organization_id)
    return [
        TranscriptMatchDTO(communication=cards[communication_id], fragments=found[:fragments_limit])
        for communication_id, found in fragments.items()
    ]


__all__ = ["find_communications", "get_communication_cards", "get_transcript_text", "search_transcripts"]
