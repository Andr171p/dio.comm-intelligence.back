from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus

import aiohttp
from pydantic import UUID4, BaseModel, EmailStr

from src.application.auth.dtos import Auth, AuthType
from src.application.auth.exceptions import UnauthorizedError

from .config import SrvIamConfig


class _Userinfo(BaseModel):
    id: UUID4
    email: EmailStr
    roles: set[str]


class SrvIamClient:
    def __init__(self, config: SrvIamConfig) -> None:
        self._config = config
        self._session: aiohttp.ClientSession | None = None

    @asynccontextmanager
    async def _get_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._config.timeout)
            self._session = aiohttp.ClientSession(base_url=str(self._config.base_url), timeout=timeout)

        yield self._session

    async def authenticate(self, token: str) -> Auth:
        """Получает аутентифицированный субъект."""

        headers = {"Authorization": f"Bearer {token}"}

        async with (
            self._get_session() as session,
            session.get("/api/v1/auth/userinfo", headers=headers) as response,
        ):
            if response.status == HTTPStatus.UNAUTHORIZED:
                raise UnauthorizedError("Invalid or expired access token.")

            response.raise_for_status()
            data = await response.json()

        userinfo = _Userinfo.model_validate(data)
        return Auth(
            id=userinfo.id,
            type=AuthType.ADMIN if "admin" in userinfo.roles else AuthType.USER,
            user=Auth.User(
                id=userinfo.id,
                email=userinfo.email,
                roles=userinfo.roles,
            )
        )

    async def close(self) -> None:
        if self._session is None or self._session.closed:
            return

        await self._session.close()
        self._session = None
