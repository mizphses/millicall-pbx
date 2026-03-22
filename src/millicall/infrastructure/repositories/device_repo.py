from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Device
from millicall.infrastructure.orm import devices_table


class DeviceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> Device:
        return Device(
            id=row.id,
            mac_address=row.mac_address,
            ip_address=row.ip_address,
            hostname=row.hostname,
            model=row.model,
            peer_id=row.peer_id,
            extension_id=row.extension_id,
            provisioned=row.provisioned,
            last_seen=row.last_seen,
        )

    async def get_all(self) -> list[Device]:
        result = await self.session.execute(
            select(devices_table).order_by(devices_table.c.mac_address)
        )
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, device_id: int) -> Device | None:
        result = await self.session.execute(
            select(devices_table).where(devices_table.c.id == device_id)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def get_by_mac(self, mac_address: str) -> Device | None:
        mac = mac_address.upper().replace("-", ":").replace(".", ":")
        result = await self.session.execute(
            select(devices_table).where(devices_table.c.mac_address == mac)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def upsert(self, device: Device) -> Device:
        """Insert or update device by MAC address."""
        mac = device.mac_address.upper().replace("-", ":").replace(".", ":")
        device.mac_address = mac

        existing = await self.get_by_mac(mac)
        if existing:
            await self.session.execute(
                update(devices_table)
                .where(devices_table.c.mac_address == mac)
                .values(
                    ip_address=device.ip_address or existing.ip_address,
                    hostname=device.hostname or existing.hostname,
                    model=device.model or existing.model,
                    last_seen=device.last_seen or datetime.now(),
                )
            )
            await self.session.commit()
            device.id = existing.id
            device.peer_id = existing.peer_id
            device.extension_id = existing.extension_id
            device.provisioned = existing.provisioned
            return device
        else:
            result = await self.session.execute(
                devices_table.insert().values(
                    mac_address=mac,
                    ip_address=device.ip_address,
                    hostname=device.hostname,
                    model=device.model,
                    peer_id=device.peer_id,
                    extension_id=device.extension_id,
                    provisioned=device.provisioned,
                    last_seen=device.last_seen or datetime.now(),
                )
            )
            await self.session.commit()
            device.id = result.inserted_primary_key[0]
            return device

    async def assign(
        self,
        device_id: int,
        peer_id: int | None,
        extension_id: int | None,
    ) -> Device | None:
        device = await self.get_by_id(device_id)
        if not device:
            return None

        await self.session.execute(
            update(devices_table)
            .where(devices_table.c.id == device_id)
            .values(
                peer_id=peer_id,
                extension_id=extension_id,
                provisioned=True,
            )
        )
        await self.session.commit()
        device.peer_id = peer_id
        device.extension_id = extension_id
        device.provisioned = True
        return device

    async def delete(self, device_id: int) -> None:
        await self.session.execute(delete(devices_table).where(devices_table.c.id == device_id))
        await self.session.commit()
