from typing import Any, cast

from sqlalchemy import CursorResult, delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.exceptions import ContactNotFoundError
from millicall.domain.models import Contact
from millicall.infrastructure.orm import contacts_table


class ContactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> Contact:
        return Contact(
            id=row.id,
            name=row.name,
            phone_number=row.phone_number,
            company=row.company,
            department=row.department,
            notes=row.notes,
        )

    async def get_all(self) -> list[Contact]:
        result = await self.session.execute(select(contacts_table).order_by(contacts_table.c.name))
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, contact_id: int) -> Contact:
        result = await self.session.execute(
            select(contacts_table).where(contacts_table.c.id == contact_id)
        )
        row = result.first()
        if row is None:
            raise ContactNotFoundError(contact_id)
        return self._row_to_model(row)

    async def search(self, query: str) -> list[Contact]:
        """Search contacts by name or phone number (partial match)."""
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(contacts_table)
            .where(
                or_(
                    contacts_table.c.name.ilike(pattern),
                    contacts_table.c.phone_number.like(pattern),
                    contacts_table.c.company.ilike(pattern),
                )
            )
            .order_by(contacts_table.c.name)
        )
        return [self._row_to_model(row) for row in result]

    async def create(self, contact: Contact) -> Contact:
        result = await self.session.execute(
            contacts_table.insert().values(
                name=contact.name,
                phone_number=contact.phone_number,
                company=contact.company,
                department=contact.department,
                notes=contact.notes,
            )
        )
        await self.session.commit()
        contact.id = cast("list[Any]", cast("CursorResult", result).inserted_primary_key)[0]
        return contact

    async def update(self, contact: Contact) -> Contact:
        if contact.id is None:
            raise ContactNotFoundError(0)

        # Verify existence
        await self.get_by_id(contact.id)

        await self.session.execute(
            update(contacts_table)
            .where(contacts_table.c.id == contact.id)
            .values(
                name=contact.name,
                phone_number=contact.phone_number,
                company=contact.company,
                department=contact.department,
                notes=contact.notes,
            )
        )
        await self.session.commit()
        return contact

    async def delete(self, contact_id: int) -> None:
        result = await self.session.execute(
            delete(contacts_table).where(contacts_table.c.id == contact_id)
        )
        if cast("CursorResult", result).rowcount == 0:
            raise ContactNotFoundError(contact_id)
        await self.session.commit()
