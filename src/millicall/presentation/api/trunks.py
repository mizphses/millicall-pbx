from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.trunk_service import TrunkService
from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import TrunkCreate, TrunkResponse, TrunkUpdate

router = APIRouter(
    prefix="/api/trunks",
    tags=["trunks"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[TrunkResponse])
async def list_trunks(session: AsyncSession = Depends(get_session)):
    service = TrunkService(session)
    trunks = await service.list_trunks()
    return [
        TrunkResponse(
            id=t.id,
            name=t.name,
            display_name=t.display_name,
            host=t.host,
            username=t.username,
            password=t.password,
            did_number=t.did_number,
            caller_id=t.caller_id,
            incoming_dest=t.incoming_dest,
            outbound_prefixes=t.outbound_prefixes,
            enabled=t.enabled,
        )
        for t in trunks
    ]


@router.get("/{trunk_id}", response_model=TrunkResponse)
async def get_trunk(trunk_id: int, session: AsyncSession = Depends(get_session)):
    service = TrunkService(session)
    t = await service.get_trunk(trunk_id)
    return TrunkResponse(
        id=t.id,
        name=t.name,
        display_name=t.display_name,
        host=t.host,
        username=t.username,
        password=t.password,
        did_number=t.did_number,
        caller_id=t.caller_id,
        incoming_dest=t.incoming_dest,
        outbound_prefixes=t.outbound_prefixes,
        enabled=t.enabled,
    )


@router.post("", response_model=TrunkResponse, status_code=201)
async def create_trunk(
    data: TrunkCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = TrunkService(session)
    t = await service.create_trunk(
        name=data.name,
        display_name=data.display_name,
        host=data.host,
        username=data.username,
        password=data.password,
        did_number=data.did_number,
        caller_id=data.caller_id,
        incoming_dest=data.incoming_dest,
        outbound_prefixes=data.outbound_prefixes,
        enabled=data.enabled,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return TrunkResponse(
        id=t.id,
        name=t.name,
        display_name=t.display_name,
        host=t.host,
        username=t.username,
        password=t.password,
        did_number=t.did_number,
        caller_id=t.caller_id,
        incoming_dest=t.incoming_dest,
        outbound_prefixes=t.outbound_prefixes,
        enabled=t.enabled,
    )


@router.put("/{trunk_id}", response_model=TrunkResponse)
async def update_trunk(
    trunk_id: int,
    data: TrunkUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = TrunkService(session)
    t = await service.update_trunk(
        trunk_id=trunk_id,
        name=data.name,
        display_name=data.display_name,
        host=data.host,
        username=data.username,
        password=data.password,
        did_number=data.did_number,
        caller_id=data.caller_id,
        incoming_dest=data.incoming_dest,
        outbound_prefixes=data.outbound_prefixes,
        enabled=data.enabled,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return TrunkResponse(
        id=t.id,
        name=t.name,
        display_name=t.display_name,
        host=t.host,
        username=t.username,
        password=t.password,
        did_number=t.did_number,
        caller_id=t.caller_id,
        incoming_dest=t.incoming_dest,
        outbound_prefixes=t.outbound_prefixes,
        enabled=t.enabled,
    )


@router.delete("/{trunk_id}", status_code=204)
async def delete_trunk(
    trunk_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = TrunkService(session)
    await service.delete_trunk(trunk_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
