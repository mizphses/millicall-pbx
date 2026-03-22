from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.device_service import DeviceService
from millicall.infrastructure.database import get_session

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def list_devices(session: AsyncSession = Depends(get_session)):
    service = DeviceService(session)
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
        }
        for d in devices
    ]


@router.post("/scan")
async def scan_devices(session: AsyncSession = Depends(get_session)):
    service = DeviceService(session)
    devices = await service.scan_dhcp_leases()
    return {"scanned": len(devices)}


@router.post("/{device_id}/auto-provision")
async def auto_provision_device(
    device_id: int,
    extension_number: str,
    display_name: str,
    session: AsyncSession = Depends(get_session),
):
    service = DeviceService(session)
    device = await service.auto_provision(device_id, extension_number, display_name)
    if not device:
        return {"error": "Device not found"}

    asterisk = AsteriskService(session)
    await asterisk.apply_config()

    return {"status": "provisioned", "device_id": device.id}
