from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import User
from millicall.infrastructure.orm import users_table


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> User:
        return User(
            id=row.id,
            username=row.username,
            hashed_password=row.hashed_password,
            display_name=row.display_name,
            is_admin=row.is_admin,
            role=row.role,
        )

    async def get_all(self) -> list[User]:
        result = await self.session.execute(select(users_table).order_by(users_table.c.id))
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(users_table).where(users_table.c.id == user_id))
        row = result.first()
        return self._row_to_model(row) if row else None

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(users_table).where(users_table.c.username == username)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def create(self, user: User) -> User:
        result = await self.session.execute(
            users_table.insert().values(
                username=user.username,
                hashed_password=user.hashed_password,
                display_name=user.display_name,
                is_admin=user.is_admin,
                role=user.role,
            )
        )
        await self.session.commit()
        user.id = result.inserted_primary_key[0]
        return user

    async def update(self, user_id: int, **kwargs) -> None:
        await self.session.execute(
            update(users_table).where(users_table.c.id == user_id).values(**kwargs)
        )
        await self.session.commit()

    async def delete(self, user_id: int) -> None:
        await self.session.execute(delete(users_table).where(users_table.c.id == user_id))
        await self.session.commit()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(users_table))
        return result.scalar() or 0
