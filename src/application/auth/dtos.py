from enum import IntEnum, auto
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ЗАГЛУШКА для Legacy IAM (текущая реализация не поддерживает multi-tenancy)
_STUB_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000000")


class AuthType(IntEnum):
    USER = auto()
    CLIENT = auto()
    ADMIN = auto()


class Auth(BaseModel):
    model_config = ConfigDict(frozen=True)

    class User(BaseModel):
        id: UUID
        email: EmailStr
        organization_id: UUID = _STUB_ORGANIZATION_ID
        roles: frozenset[str] = Field(default_factory=frozenset)

    id: UUID
    type: AuthType

    user: User | None = None


class AuthUser(Auth):
    """Авторизованный пользователь."""
    user: Auth.User
