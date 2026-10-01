from typing import Annotated

import hashlib
from collections.abc import Callable

from ddf.infra.cache import InMemoryCache
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.application.auth.dtos import Auth, AuthType
from src.application.auth.exceptions import PermissionDeniedError, UnauthorizedError
from src.infra.services.iam import SrvIamClient, SrvIamConfig

_CACHE_TLL = 10 * 60

bearer_scheme = HTTPBearer(auto_error=False, description="Access токен DIOS")

iam_config = SrvIamConfig()  # type: ignore
iam_client = SrvIamClient(iam_config)

auth_cache = InMemoryCache[Auth]()


async def get_current_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Auth:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing or invalid credentials.")

    token = credentials.credentials
    cache_key = f"iam:auth:{hashlib.sha256(token.encode()).hexdigest()}"

    if (cached_auth := await auth_cache.get(cache_key)) is not None:
        return cached_auth

    auth = await iam_client.authenticate(token)
    await auth_cache.set(cache_key, auth, ttl=_CACHE_TLL)
    return auth


CurrentAuth = Annotated[Auth, Depends(get_current_auth)]


def require_auth_type(required_type: AuthType) -> Callable[[Auth], Auth]:
    def dependency(auth: Annotated[Auth, Depends(get_current_auth)]) -> Auth:
        if auth.type != required_type:
            raise PermissionDeniedError(f"Access denied for auth type: {auth.type.name!r}.")

        return auth
    return dependency


require_auth_user = Security(require_auth_type(AuthType.USER))

__all__ = ["CurrentAuth", "require_auth_user"]
