import logging
import re
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Device
from millicall.infrastructure.repositories.device_repo import DeviceRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.peer_repo import PeerRepository

logger = logging.getLogger(__name__)


class DeviceService:
    def __init__(self, session: AsyncSession):
        self.device_repo = DeviceRepository(session)
        self.peer_repo = PeerRepository(session)
        self.extension_repo = ExtensionRepository(session)

    async def list_devices(self) -> list[Device]:
        return await self.device_repo.get_all()

    async def get_device(self, device_id: int) -> Device | None:
        return await self.device_repo.get_by_id(device_id)

    async def get_device_by_mac(self, mac: str) -> Device | None:
        return await self.device_repo.get_by_mac(mac)

    async def assign_device(
        self,
        device_id: int,
        peer_id: int | None,
        extension_id: int | None,
    ) -> Device | None:
        return await self.device_repo.assign(device_id, peer_id, extension_id)

    async def auto_provision(
        self,
        device_id: int,
        extension_number: str,
        display_name: str,
    ) -> Device | None:
        """Create peer + extension and assign to device automatically."""
        device = await self.device_repo.get_by_id(device_id)
        if not device:
            return None

        username = f"phone{extension_number}"
        password = extension_number

        # Create extension
        from millicall.application.extension_service import ExtensionService
        from millicall.application.peer_service import PeerService

        ext_service = ExtensionService(self.device_repo.session)
        peer_service = PeerService(self.device_repo.session)

        ext = await ext_service.create_extension(
            number=extension_number,
            display_name=display_name,
        )

        peer = await peer_service.create_peer(
            username=username,
            password=password,
            extension_id=ext.id,
        )

        # Update extension with peer_id
        await ext_service.update_extension(
            extension_id=ext.id,
            number=ext.number,
            display_name=ext.display_name,
            enabled=True,
            peer_id=peer.id,
        )

        return await self.device_repo.assign(device_id, peer.id, ext.id)

    async def scan_dhcp_leases(self, leases_path: str = "/var/lib/misc/dnsmasq.leases") -> list[Device]:
        """Read dnsmasq leases file and upsert devices."""
        path = Path(leases_path)
        if not path.exists():
            logger.warning("DHCP leases file not found: %s", leases_path)
            return []

        devices = []
        for line in path.read_text().strip().splitlines():
            parts = line.split()
            if len(parts) >= 4:
                # Format: timestamp mac ip hostname *
                mac = parts[1].upper()
                ip = parts[2]
                hostname = parts[3] if parts[3] != "*" else None

                device = Device(
                    mac_address=mac,
                    ip_address=ip,
                    hostname=hostname,
                    last_seen=datetime.fromtimestamp(int(parts[0])),
                )
                device = await self.device_repo.upsert(device)
                devices.append(device)

        return devices
