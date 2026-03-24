from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.exceptions import DuplicatePeerError, PeerNotFoundError
from millicall.domain.models import Peer
from millicall.infrastructure.orm import peers_table


class PeerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> Peer:
        return Peer(
            id=row.id,
            username=row.username,
            password=row.password,
            transport=row.transport,
            codecs=row.codecs.split(",") if row.codecs else ["ulaw", "alaw"],
            ip_address=row.ip_address,
            extension_id=row.extension_id,
        )

    async def get_all(self) -> list[Peer]:
        result = await self.session.execute(select(peers_table).order_by(peers_table.c.username))
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, peer_id: int) -> Peer:
        result = await self.session.execute(select(peers_table).where(peers_table.c.id == peer_id))
        row = result.first()
        if row is None:
            raise PeerNotFoundError(peer_id)
        return self._row_to_model(row)

    async def get_by_username(self, username: str) -> Peer | None:
        result = await self.session.execute(
            select(peers_table).where(peers_table.c.username == username)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def create(self, peer: Peer) -> Peer:
        existing = await self.get_by_username(peer.username)
        if existing:
            raise DuplicatePeerError(peer.username)

        result = await self.session.execute(
            peers_table.insert().values(
                username=peer.username,
                password=peer.password,
                transport=peer.transport,
                codecs=",".join(peer.codecs),
                ip_address=peer.ip_address,
                extension_id=peer.extension_id,
            )
        )
        await self.session.commit()
        peer.id = cast("list[Any]", cast("CursorResult", result).inserted_primary_key)[0]
        return peer

    async def update(self, peer: Peer) -> Peer:
        if peer.id is None:
            raise PeerNotFoundError(0)

        existing = await self.get_by_username(peer.username)
        if existing and existing.id != peer.id:
            raise DuplicatePeerError(peer.username)

        await self.session.execute(
            update(peers_table)
            .where(peers_table.c.id == peer.id)
            .values(
                username=peer.username,
                password=peer.password,
                transport=peer.transport,
                codecs=",".join(peer.codecs),
                ip_address=peer.ip_address,
                extension_id=peer.extension_id,
            )
        )
        await self.session.commit()
        return peer

    async def delete(self, peer_id: int) -> None:
        result = await self.session.execute(delete(peers_table).where(peers_table.c.id == peer_id))
        if cast("CursorResult", result).rowcount == 0:
            raise PeerNotFoundError(peer_id)
        await self.session.commit()
