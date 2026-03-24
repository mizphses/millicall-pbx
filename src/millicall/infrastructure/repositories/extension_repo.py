from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.exceptions import DuplicateExtensionError, ExtensionNotFoundError
from millicall.domain.models import Extension
from millicall.infrastructure.orm import extensions_table


class ExtensionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> Extension:
        return Extension(
            id=row.id,
            number=row.number,
            display_name=row.display_name,
            enabled=row.enabled,
            peer_id=row.peer_id,
            type=row.type if hasattr(row, "type") else "phone",
            ai_agent_id=row.ai_agent_id if hasattr(row, "ai_agent_id") else None,
        )

    async def get_all(self) -> list[Extension]:
        result = await self.session.execute(
            select(extensions_table).order_by(extensions_table.c.number)
        )
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, extension_id: int) -> Extension:
        result = await self.session.execute(
            select(extensions_table).where(extensions_table.c.id == extension_id)
        )
        row = result.first()
        if row is None:
            raise ExtensionNotFoundError(extension_id)
        return self._row_to_model(row)

    async def get_by_number(self, number: str) -> Extension | None:
        result = await self.session.execute(
            select(extensions_table).where(extensions_table.c.number == number)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def create(self, ext: Extension) -> Extension:
        existing = await self.get_by_number(ext.number)
        if existing:
            raise DuplicateExtensionError(ext.number)

        result = await self.session.execute(
            extensions_table.insert().values(
                number=ext.number,
                display_name=ext.display_name,
                enabled=ext.enabled,
                peer_id=ext.peer_id,
                type=ext.type,
                ai_agent_id=ext.ai_agent_id,
            )
        )
        await self.session.commit()
        ext.id = cast("list[Any]", cast("CursorResult", result).inserted_primary_key)[0]
        return ext

    async def update(self, ext: Extension) -> Extension:
        if ext.id is None:
            raise ExtensionNotFoundError(0)

        # Check for duplicate number (excluding self)
        existing = await self.get_by_number(ext.number)
        if existing and existing.id != ext.id:
            raise DuplicateExtensionError(ext.number)

        await self.session.execute(
            update(extensions_table)
            .where(extensions_table.c.id == ext.id)
            .values(
                number=ext.number,
                display_name=ext.display_name,
                enabled=ext.enabled,
                peer_id=ext.peer_id,
                type=ext.type,
                ai_agent_id=ext.ai_agent_id,
            )
        )
        await self.session.commit()
        return ext

    async def delete(self, extension_id: int) -> None:
        result = await self.session.execute(
            delete(extensions_table).where(extensions_table.c.id == extension_id)
        )
        if cast("CursorResult", result).rowcount == 0:
            raise ExtensionNotFoundError(extension_id)
        await self.session.commit()
