from http import HTTPStatus
from uuid import UUID

from src.application.communications.dtos import CommunicationResponse, UpdateCommunicationDTO
from src.infra.services.base import SrvBaseClient


class SrvCommunicationsClient(SrvBaseClient):

    async def get_communication(self, communication_id: UUID) -> CommunicationResponse | None:
        async with (
            self._get_token_session() as session,
            session.get(f"/api/service/v1/communications/{communication_id}") as response,
        ):
            if response.status == HTTPStatus.NOT_FOUND:
                return None

            response.raise_for_status()
            data = await response.json()

        return CommunicationResponse.model_validate(data)

    async def update_communication(
        self,
        communication_id: UUID,
        dto: UpdateCommunicationDTO,
    ) -> CommunicationResponse | None:
        url = f"/api/service/v1/communications/{communication_id}"
        # Без exclude_unset: он выкидывает дискриминатор ``type`` у вложенных представлений
        payload = dto.model_dump(mode="json", by_alias=True)

        async with (
            self._get_token_session() as session,
            session.patch(url, json=payload) as response,
        ):
            if response.status == HTTPStatus.NOT_FOUND:
                return None

            response.raise_for_status()
            data = await response.json()

        return CommunicationResponse.model_validate(data)
