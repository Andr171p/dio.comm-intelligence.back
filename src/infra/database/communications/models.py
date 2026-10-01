from typing import Any

from datetime import datetime
from uuid import UUID

from ddf.infra.database.sqlalchemy import Base, EntityMixin
from ddf.infra.database.sqlalchemy.types import DatatimeTz, StrNull, UuidNull
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CommunicationOrm(EntityMixin, Base):
    __tablename__ = "communications"

    organization_id: Mapped[UUID] = mapped_column(index=True)
    original_media_id: Mapped[UuidNull]
    external_id: Mapped[StrNull]
    external_source: Mapped[StrNull]

    title: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(32))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    participants: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    started_at: Mapped[DatatimeTz]
    ended_at: Mapped[DatatimeTz]

    representations: Mapped[list["CommunicationRepresentationOrm"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_communications_external", "external_source", "external_id"),)


class CommunicationRepresentationOrm(Base):
    """Представление коммуникации, одно на каждый тип."""

    __tablename__ = "communication_representations"

    communication_id: Mapped[UUID] = mapped_column(
        ForeignKey("communications.id", ondelete="CASCADE"), primary_key=True,
    )
    type: Mapped[str] = mapped_column(String(32), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )
