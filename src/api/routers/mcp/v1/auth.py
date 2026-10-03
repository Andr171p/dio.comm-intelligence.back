from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from src.api.dependencies.auth import authenticate
from src.application.auth.dtos import AuthType, AuthUser
from src.application.auth.exceptions import UnauthorizedError


class DiosAccessToken(AccessToken):
    """Access токен DIOS вместе с аутентифицированным пользователем."""

    auth: AuthUser


class DiosTokenVerifier:
    """Проверяет Bearer токен DIOS через IAM, MCP доступен только пользователям."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            auth = await authenticate(token)
        except UnauthorizedError:
            return None

        if auth.type != AuthType.USER or auth.user is None:
            return None

        return DiosAccessToken(
            token=token,
            client_id=str(auth.id),
            subject=str(auth.id),
            scopes=sorted(auth.user.roles),
            auth=AuthUser.model_validate(auth, from_attributes=True),
        )


def get_current_user() -> AuthUser:
    """Пользователь текущего MCP запроса (анонимные запросы отсекает middleware SDK)."""

    access_token = get_access_token()

    if not isinstance(access_token, DiosAccessToken):
        raise UnauthorizedError("Missing or invalid credentials.")

    return access_token.auth
