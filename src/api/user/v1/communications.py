from fastapi import APIRouter, status

from src.application.communications.crud import CommunicationCrudDep
from src.application.communications.dtos import CommunicationResponse, CreateCommunicationDTO

router = APIRouter(prefix="/communications", tags=["Communications"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Создать коммуникацию",
)
async def create_communication(
    dto: CreateCommunicationDTO,
    crud: CommunicationCrudDep,
) -> CommunicationResponse:
    return await crud.create(dto)


@router.get(
    "/{communication_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить коммуникацию",
)
async def get_communication(): ...
