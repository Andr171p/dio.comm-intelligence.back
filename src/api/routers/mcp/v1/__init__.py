"""MCP сервер коммуникаций (streamable HTTP, только для аутентифицированных пользователей DIOS)."""

from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl

from .auth import DiosTokenVerifier
from .config import mcp_config
from .tools import find_communications, get_communication_transcript, search_transcripts

_INSTRUCTIONS = """\
Доступ к коммуникациям организации пользователя (совещания, звонки) и их расшифровкам.

Сценарий «какие решения приняли вчера на совещании»:
1. find_communications за нужный период (относительные даты переводи в абсолютные с часовым поясом
   пользователя), выбери коммуникацию по названию, повестке и участникам;
2. get_communication_transcript - читай страницы, пока next_offset не null;
3. отвечай только по тексту расшифровки и ссылайся на таймкоды [чч:мм:сс].

Если тема известна, а встреча нет - search_transcripts. Спикеры в расшифровке обезличены (speaker_N).
"""

mcp_server = MCPServer(
    name="dio-communications",
    instructions=_INSTRUCTIONS,
    token_verifier=DiosTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(mcp_config.issuer_url),
        resource_server_url=AnyHttpUrl(mcp_config.resource_url),
        validate_token_resource=False,  # токены DIOS не привязаны к resource, проверяет IAM
    ),
)

for tool in (find_communications, get_communication_transcript, search_transcripts):
    mcp_server.add_tool(tool, structured_output=True)

# Stateless + JSON: без серверных сессий, API масштабируется горизонтально
mcp_app = mcp_server.streamable_http_app(
    streamable_http_path="/v1",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(allowed_hosts=mcp_config.allowed_hosts),
)

__all__ = ["mcp_app", "mcp_server"]
