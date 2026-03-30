"""Repository for on-demand call entries."""

from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import OnDemandCall
from millicall.infrastructure.orm import ondemand_calls_table


class OnDemandCallRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[OnDemandCall]:
        result = await self.session.execute(
            select(ondemand_calls_table).order_by(ondemand_calls_table.c.id)
        )
        return [
            OnDemandCall(
                id=row.id,
                label=row.label,
                phone_number=row.phone_number,
                enabled=row.enabled,
            )
            for row in result
        ]

    async def get_by_id(self, call_id: int) -> OnDemandCall | None:
        result = await self.session.execute(
            select(ondemand_calls_table).where(ondemand_calls_table.c.id == call_id)
        )
        row = result.first()
        if not row:
            return None
        return OnDemandCall(
            id=row.id,
            label=row.label,
            phone_number=row.phone_number,
            enabled=row.enabled,
        )

    async def create(self, entry: OnDemandCall) -> OnDemandCall:
        result = await self.session.execute(
            ondemand_calls_table.insert().values(
                label=entry.label,
                phone_number=entry.phone_number,
                enabled=entry.enabled,
            )
        )
        await self.session.commit()
        entry.id = cast("list[Any]", cast("CursorResult", result).inserted_primary_key)[0]
        return entry

    async def update(self, call_id: int, **kwargs) -> None:
        await self.session.execute(
            update(ondemand_calls_table)
            .where(ondemand_calls_table.c.id == call_id)
            .values(**kwargs)
        )
        await self.session.commit()

    async def delete(self, call_id: int) -> None:
        await self.session.execute(
            delete(ondemand_calls_table).where(ondemand_calls_table.c.id == call_id)
        )
        await self.session.commit()
