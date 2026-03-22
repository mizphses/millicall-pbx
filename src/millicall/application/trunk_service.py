from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Trunk
from millicall.infrastructure.repositories.trunk_repo import TrunkRepository


class TrunkService:
    def __init__(self, session: AsyncSession):
        self.repo = TrunkRepository(session)

    async def list_trunks(self) -> list[Trunk]:
        return await self.repo.get_all()

    async def get_trunk(self, trunk_id: int) -> Trunk:
        return await self.repo.get_by_id(trunk_id)

    async def create_trunk(
        self,
        name: str,
        display_name: str,
        host: str,
        username: str,
        password: str,
        did_number: str = "",
        caller_id: str = "",
        incoming_dest: str = "",
        outbound_prefixes: str = "",
        enabled: bool = True,
    ) -> Trunk:
        trunk = Trunk(
            name=name,
            display_name=display_name,
            host=host,
            username=username,
            password=password,
            did_number=did_number,
            caller_id=caller_id,
            incoming_dest=incoming_dest,
            outbound_prefixes=outbound_prefixes,
            enabled=enabled,
        )
        return await self.repo.create(trunk)

    async def update_trunk(
        self,
        trunk_id: int,
        name: str,
        display_name: str,
        host: str,
        username: str,
        password: str,
        did_number: str = "",
        caller_id: str = "",
        incoming_dest: str = "",
        outbound_prefixes: str = "",
        enabled: bool = True,
    ) -> Trunk:
        trunk = Trunk(
            id=trunk_id,
            name=name,
            display_name=display_name,
            host=host,
            username=username,
            password=password,
            did_number=did_number,
            caller_id=caller_id,
            incoming_dest=incoming_dest,
            outbound_prefixes=outbound_prefixes,
            enabled=enabled,
        )
        return await self.repo.update(trunk)

    async def delete_trunk(self, trunk_id: int) -> None:
        await self.repo.delete(trunk_id)
