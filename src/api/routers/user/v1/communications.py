from uuid import UUID

from fastapi import APIRouter, status

from src.api.dependencies.auth import CurrentUser
from src.api.dependencies.communications import CommunicationCrudDep
from src.application.communications.crud import CreateCommunicationOptions, ReadCommunicationOptions
from src.application.communications.dtos import CommunicationResponse, CreateCommunicationDTO

router = APIRouter(prefix="/communications", tags=["Communications"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Создать коммуникацию",
    description="Коммуникация создаётся сразу, подготовка к анализу (транскрибация) идёт асинхронно.",
)
async def create_communication(
    dto: CreateCommunicationDTO,
    crud: CommunicationCrudDep,
    auth: CurrentUser,
) -> CommunicationResponse:
    options = CreateCommunicationOptions(organization_id=auth.user.organization_id)
    return await crud.create(dto, options)


@router.get(
    "/{communication_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить коммуникацию",
)
async def get_communication(
    communication_id: UUID,
    crud: CommunicationCrudDep,
    auth: CurrentUser,
) -> CommunicationResponse:
    options = ReadCommunicationOptions(organization_id=auth.user.organization_id)
    return await crud.read(communication_id, options)
