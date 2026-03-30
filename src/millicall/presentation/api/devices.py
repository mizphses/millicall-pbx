import contextlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.device_service import DeviceService
from millicall.application.extension_service import ExtensionService
from millicall.application.peer_service import PeerService
from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.presentation.auth import get_current_user, require_admin

router = APIRouter(
    prefix="/api/devices",
    tags=["devices"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_devices(session: AsyncSession = Depends(get_session)):
    service = DeviceService(session)
    # Auto-scan DHCP leases on every list request
    with contextlib.suppress(Exception):
        await service.scan_dhcp_leases()
    devices = await service.list_devices()
    return [
        {
            "id": d.id,
            "mac_address": d.mac_address,
            "ip_address": d.ip_address,
            "hostname": d.hostname,
            "model": d.model,
            "peer_id": d.peer_id,
            "extension_id": d.extension_id,
            "provisioned": d.provisioned,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "active": d.active,
        }
        for d in devices
    ]


@router.post("/scan")
async def scan_devices(
    session: AsyncSession = Depends(get_session), _admin: User = Depends(require_admin)
):
    service = DeviceService(session)
    devices = await service.scan_dhcp_leases()
    return {"scanned": len(devices)}


class QuickProvisionRequest(BaseModel):
    extension_number: str
    display_name: str


class AssignExtensionRequest(BaseModel):
    extension_id: int


@router.post("/{device_id}/quick-provision")
async def quick_provision(
    device_id: int,
    data: QuickProvisionRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """1アクションでPeer作成→Extension作成→デバイス紐付けを完了する。"""
    device_service = DeviceService(session)
    device = await device_service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # パスワード自動生成（12文字英数字）
    password = secrets.token_urlsafe(9)  # 12 chars
    username = f"ext{data.extension_number}"

    # Peer作成
    peer_service = PeerService(session)
    peer = await peer_service.create_peer(
        username=username,
        password=password,
    )

    # Extension作成 + Peer紐付け
    ext_service = ExtensionService(session)
    ext = await ext_service.create_extension(
        number=data.extension_number,
        display_name=data.display_name,
        peer_id=peer.id,
    )

    # デバイスに割当
    await device_service.assign_device(device_id, peer_id=peer.id, extension_id=ext.id)

    # Asterisk設定反映 + check-sync送信
    asterisk = AsteriskService(session)
    await asterisk.apply_config()

    return {
        "status": "provisioned",
        "device_id": device.id,
        "extension_number": data.extension_number,
        "sip_username": username,
        "sip_password": password,
    }


@router.post("/{device_id}/assign-extension")
async def assign_extension_to_device(
    device_id: int,
    data: AssignExtensionRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """既存の内線をデバイスに割り当てる。"""
    ext_repo = ExtensionRepository(session)
    ext = await ext_repo.get_by_id(data.extension_id)

    device_service = DeviceService(session)
    device = await device_service.assign_device(
        device_id=device_id,
        peer_id=ext.peer_id,
        extension_id=ext.id,
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    asterisk = AsteriskService(session)
    await asterisk.apply_config()

    return {"status": "assigned", "device_id": device.id}


@router.post("/{device_id}/resync")
async def resync_device(
    device_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """デバイスにHTTPリシンクを送信してプロビジョニング設定を再取得させる。"""
    from millicall.infrastructure.asterisk.reloader import AsteriskReloader

    device_service = DeviceService(session)
    device = await device_service.get_device(device_id)
    if not device or not device.ip_address:
        raise HTTPException(status_code=404, detail="Device not found or no IP")

    reloader = AsteriskReloader()
    success = reloader.send_http_resync(device.ip_address)

    # SIP check-sync as fallback
    if device.peer_id:
        from millicall.infrastructure.repositories.peer_repo import PeerRepository

        peer_repo = PeerRepository(session)
        peer = await peer_repo.get_by_id(device.peer_id)
        with contextlib.suppress(Exception):
            reloader.send_check_sync(peer.username)

    return {"status": "sent", "http_resync": success}
