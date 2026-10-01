from uuid import UUID

from fastapi import APIRouter, status

from src.api.dependencies.communications import CommunicationCrudDep
from src.application.communications.dtos import CommunicationResponse, UpdateCommunicationDTO

router = APIRouter(prefix="/communications", tags=["Service: Communications"])


@router.get(
    "/{communication_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить коммуникацию",
)
async def get_communication(communication_id: UUID, crud: CommunicationCrudDep) -> CommunicationResponse:
    return await crud.read(communication_id)


@router.patch(
    "/{communication_id}",
    status_code=status.HTTP_200_OK,
    summary="Обновить коммуникацию",
    description="Переданные представления заменяют существующие того же типа.",
)
async def update_communication(
    communication_id: UUID,
    dto: UpdateCommunicationDTO,
    crud: CommunicationCrudDep,
) -> CommunicationResponse:
    return await crud.update(communication_id, dto)
