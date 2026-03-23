from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.peer_service import PeerService
from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import PeerCreate, PeerResponse, PeerUpdate

router = APIRouter(
    prefix="/api/peers",
    tags=["peers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[PeerResponse])
async def list_peers(session: AsyncSession = Depends(get_session)):
    service = PeerService(session)
    peers = await service.list_peers()
    return [
        PeerResponse(
            id=p.id,
            username=p.username,
            password=p.password,
            transport=p.transport,
            codecs=p.codecs,
            ip_address=p.ip_address,
            extension_id=p.extension_id,
        )
        for p in peers
    ]


@router.get("/{peer_id}", response_model=PeerResponse)
async def get_peer(peer_id: int, session: AsyncSession = Depends(get_session)):
    service = PeerService(session)
    p = await service.get_peer(peer_id)
    return PeerResponse(
        id=p.id,
        username=p.username,
        password=p.password,
        transport=p.transport,
        codecs=p.codecs,
        ip_address=p.ip_address,
        extension_id=p.extension_id,
    )


@router.post("", response_model=PeerResponse, status_code=201)
async def create_peer(
    data: PeerCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = PeerService(session)
    p = await service.create_peer(
        username=data.username,
        password=data.password,
        transport=data.transport,
        codecs=data.codecs,
        ip_address=data.ip_address,
        extension_id=data.extension_id,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return PeerResponse(
        id=p.id,
        username=p.username,
        password=p.password,
        transport=p.transport,
        codecs=p.codecs,
        ip_address=p.ip_address,
        extension_id=p.extension_id,
    )


@router.put("/{peer_id}", response_model=PeerResponse)
async def update_peer(
    peer_id: int,
    data: PeerUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = PeerService(session)
    p = await service.update_peer(
        peer_id=peer_id,
        username=data.username,
        password=data.password,
        transport=data.transport,
        codecs=data.codecs,
        ip_address=data.ip_address,
        extension_id=data.extension_id,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return PeerResponse(
        id=p.id,
        username=p.username,
        password=p.password,
        transport=p.transport,
        codecs=p.codecs,
        ip_address=p.ip_address,
        extension_id=p.extension_id,
    )


@router.delete("/{peer_id}", status_code=204)
async def delete_peer(
    peer_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = PeerService(session)
    await service.delete_peer(peer_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
