from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.extension_service import ExtensionService
from millicall.infrastructure.database import get_session
from millicall.domain.models import User
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import ExtensionCreate, ExtensionResponse, ExtensionUpdate

router = APIRouter(
    prefix="/api/extensions",
    tags=["extensions"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ExtensionResponse])
async def list_extensions(session: AsyncSession = Depends(get_session)):
    service = ExtensionService(session)
    extensions = await service.list_extensions()
    return [
        ExtensionResponse(
            id=e.id,
            number=e.number,
            display_name=e.display_name,
            enabled=e.enabled,
            peer_id=e.peer_id,
            type=e.type,
            ai_agent_id=e.ai_agent_id,
        )
        for e in extensions
    ]


@router.get("/{extension_id}", response_model=ExtensionResponse)
async def get_extension(extension_id: int, session: AsyncSession = Depends(get_session)):
    service = ExtensionService(session)
    e = await service.get_extension(extension_id)
    return ExtensionResponse(
        id=e.id,
        number=e.number,
        display_name=e.display_name,
        enabled=e.enabled,
        peer_id=e.peer_id,
        type=e.type,
        ai_agent_id=e.ai_agent_id,
    )


@router.post("", response_model=ExtensionResponse, status_code=201)
async def create_extension(
    data: ExtensionCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = ExtensionService(session)
    e = await service.create_extension(
        number=data.number,
        display_name=data.display_name,
        enabled=data.enabled,
        peer_id=data.peer_id,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return ExtensionResponse(
        id=e.id,
        number=e.number,
        display_name=e.display_name,
        enabled=e.enabled,
        peer_id=e.peer_id,
        type=e.type,
        ai_agent_id=e.ai_agent_id,
    )


@router.put("/{extension_id}", response_model=ExtensionResponse)
async def update_extension(
    extension_id: int,
    data: ExtensionUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = ExtensionService(session)
    e = await service.update_extension(
        extension_id=extension_id,
        number=data.number,
        display_name=data.display_name,
        enabled=data.enabled,
        peer_id=data.peer_id,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return ExtensionResponse(
        id=e.id,
        number=e.number,
        display_name=e.display_name,
        enabled=e.enabled,
        peer_id=e.peer_id,
        type=e.type,
        ai_agent_id=e.ai_agent_id,
    )


@router.delete("/{extension_id}", status_code=204)
async def delete_extension(
    extension_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = ExtensionService(session)
    await service.delete_extension(extension_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
