from ddf.infra.database.sqlalchemy import SqlAlchemyRepository

from src.domain.communications.models import Communication

from . import data_mapper
from .models import CommunicationOrm


class SqlAlchemyCommunicationRepository(SqlAlchemyRepository[Communication, CommunicationOrm]):
    model = CommunicationOrm
    data_mapper = data_mapper  # type: ignore[assignment]
