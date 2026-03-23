from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.exceptions import DuplicateTrunkError, TrunkNotFoundError
from millicall.domain.models import Trunk
from millicall.infrastructure.orm import trunks_table


class TrunkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> Trunk:
        return Trunk(
            id=row.id,
            name=row.name,
            display_name=row.display_name,
            host=row.host,
            username=row.username,
            password=row.password,
            did_number=row.did_number,
            caller_id=row.caller_id,
            incoming_dest=row.incoming_dest,
            outbound_prefixes=row.outbound_prefixes,
            enabled=row.enabled,
        )

    async def get_all(self) -> list[Trunk]:
        result = await self.session.execute(select(trunks_table).order_by(trunks_table.c.name))
        return [self._row_to_model(row) for row in result]

    async def get_all_enabled(self) -> list[Trunk]:
        result = await self.session.execute(
            select(trunks_table).where(trunks_table.c.enabled).order_by(trunks_table.c.name)
        )
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, trunk_id: int) -> Trunk:
        result = await self.session.execute(
            select(trunks_table).where(trunks_table.c.id == trunk_id)
        )
        row = result.first()
        if not row:
            raise TrunkNotFoundError(trunk_id)
        return self._row_to_model(row)

    async def get_by_name(self, name: str) -> Trunk | None:
        result = await self.session.execute(select(trunks_table).where(trunks_table.c.name == name))
        row = result.first()
        return self._row_to_model(row) if row else None

    async def create(self, trunk: Trunk) -> Trunk:
        existing = await self.get_by_name(trunk.name)
        if existing:
            raise DuplicateTrunkError(trunk.name)
        result = await self.session.execute(
            trunks_table.insert().values(
                name=trunk.name,
                display_name=trunk.display_name,
                host=trunk.host,
                username=trunk.username,
                password=trunk.password,
                did_number=trunk.did_number,
                caller_id=trunk.caller_id,
                incoming_dest=trunk.incoming_dest,
                outbound_prefixes=trunk.outbound_prefixes,
                enabled=trunk.enabled,
            )
        )
        await self.session.commit()
        trunk.id = result.inserted_primary_key[0]
        return trunk

    async def update(self, trunk: Trunk) -> Trunk:
        existing = await self.get_by_name(trunk.name)
        if existing and existing.id != trunk.id:
            raise DuplicateTrunkError(trunk.name)
        from sqlalchemy import update

        await self.session.execute(
            update(trunks_table)
            .where(trunks_table.c.id == trunk.id)
            .values(
                name=trunk.name,
                display_name=trunk.display_name,
                host=trunk.host,
                username=trunk.username,
                password=trunk.password,
                did_number=trunk.did_number,
                caller_id=trunk.caller_id,
                incoming_dest=trunk.incoming_dest,
                outbound_prefixes=trunk.outbound_prefixes,
                enabled=trunk.enabled,
            )
        )
        await self.session.commit()
        return trunk

    async def delete(self, trunk_id: int) -> None:
        from sqlalchemy import delete

        await self.session.execute(delete(trunks_table).where(trunks_table.c.id == trunk_id))
        await self.session.commit()
