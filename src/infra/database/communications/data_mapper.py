from typing import Any

from pydantic import TypeAdapter

from src.domain.communications.models import Communication, ExternalRef, Participant
from src.domain.communications.types import CommunicationType, RepresentationType
from src.domain.communications.vo import (
    CallMeta,
    ChatRepresentation,
    ConferenceMeta,
    Period,
    TextRepresentation,
    TranscriptRepresentation,
)

from .models import CommunicationOrm, CommunicationRepresentationOrm

_META_ADAPTERS: dict[CommunicationType, TypeAdapter[Any]] = {
    CommunicationType.CALL: TypeAdapter(CallMeta),
    CommunicationType.CONFERENCE: TypeAdapter(ConferenceMeta),
}

_REPRESENTATION_ADAPTERS: dict[RepresentationType, TypeAdapter[Any]] = {
    RepresentationType.TRANSCRIPT: TypeAdapter(TranscriptRepresentation),
    RepresentationType.CHAT: TypeAdapter(ChatRepresentation),
    RepresentationType.TEXT: TypeAdapter(TextRepresentation),
}

_PARTICIPANTS_ADAPTER = TypeAdapter(tuple[Participant, ...])


def to_model(entity: Communication) -> CommunicationOrm:
    return CommunicationOrm(
        id=entity.id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        deleted_at=entity.deleted_at,
        organization_id=entity.organization_id,
        original_media_id=entity.original_media_id,
        external_id=entity.external.id if entity.external else None,
        external_source=entity.external.source if entity.external else None,
        title=entity.title,
        type=entity.type,
        meta=_META_ADAPTERS[entity.type].dump_python(entity.meta, mode="json"),
        raw_data=dict(entity.raw_data),
        participants=_PARTICIPANTS_ADAPTER.dump_python(entity.participants, mode="json"),
        started_at=entity.period.started_at,
        ended_at=entity.period.ended_at,
        representations=[
            CommunicationRepresentationOrm(
                communication_id=entity.id,
                type=representation.type,
                payload=_REPRESENTATION_ADAPTERS[representation.type].dump_python(
                    representation, mode="json",
                ),
            )
            for representation in entity.representations
        ],
    )


def from_model(model: CommunicationOrm) -> Communication:
    communication_type = CommunicationType(model.type)
    external = (
        ExternalRef(id=model.external_id, source=model.external_source)
        if model.external_id is not None and model.external_source is not None
        else None
    )

    return Communication(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        organization_id=model.organization_id,
        original_media_id=model.original_media_id,
        external=external,
        title=model.title,
        type=communication_type,
        meta=_META_ADAPTERS[communication_type].validate_python(model.meta),
        raw_data=model.raw_data,
        participants=_PARTICIPANTS_ADAPTER.validate_python(model.participants),
        period=Period(started_at=model.started_at, ended_at=model.ended_at),
        representations=[
            _REPRESENTATION_ADAPTERS[RepresentationType(representation.type)].validate_python(
                representation.payload,
            )
            for representation in model.representations
        ],
    )


__all__ = ["from_model", "to_model"]
