from ddf.application.repositories import Repository

from src.domain.communications.models import Communication

type CommunicationRepository = Repository[Communication]

__all__ = ["CommunicationRepository"]
