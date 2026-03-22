from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Peer
from millicall.infrastructure.repositories.peer_repo import PeerRepository


class PeerService:
    def __init__(self, session: AsyncSession):
        self.repo = PeerRepository(session)

    async def list_peers(self) -> list[Peer]:
        return await self.repo.get_all()

    async def get_peer(self, peer_id: int) -> Peer:
        return await self.repo.get_by_id(peer_id)

    async def create_peer(
        self,
        username: str,
        password: str,
        transport: str = "udp",
        codecs: list[str] | None = None,
        ip_address: str | None = None,
        extension_id: int | None = None,
    ) -> Peer:
        peer = Peer(
            username=username,
            password=password,
            transport=transport,
            codecs=codecs or ["ulaw", "alaw"],
            ip_address=ip_address,
            extension_id=extension_id,
        )
        return await self.repo.create(peer)

    async def update_peer(
        self,
        peer_id: int,
        username: str,
        password: str,
        transport: str = "udp",
        codecs: list[str] | None = None,
        ip_address: str | None = None,
        extension_id: int | None = None,
    ) -> Peer:
        peer = Peer(
            id=peer_id,
            username=username,
            password=password,
            transport=transport,
            codecs=codecs or ["ulaw", "alaw"],
            ip_address=ip_address,
            extension_id=extension_id,
        )
        return await self.repo.update(peer)

    async def delete_peer(self, peer_id: int) -> None:
        await self.repo.delete(peer_id)
