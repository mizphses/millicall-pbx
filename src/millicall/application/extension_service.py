from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Extension
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository


class ExtensionService:
    def __init__(self, session: AsyncSession):
        self.repo = ExtensionRepository(session)

    async def list_extensions(self) -> list[Extension]:
        return await self.repo.get_all()

    async def get_extension(self, extension_id: int) -> Extension:
        return await self.repo.get_by_id(extension_id)

    async def create_extension(
        self,
        number: str,
        display_name: str,
        enabled: bool = True,
        peer_id: int | None = None,
    ) -> Extension:
        ext = Extension(
            number=number,
            display_name=display_name,
            enabled=enabled,
            peer_id=peer_id,
        )
        return await self.repo.create(ext)

    async def update_extension(
        self,
        extension_id: int,
        number: str,
        display_name: str,
        enabled: bool = True,
        peer_id: int | None = None,
    ) -> Extension:
        ext = Extension(
            id=extension_id,
            number=number,
            display_name=display_name,
            enabled=enabled,
            peer_id=peer_id,
        )
        return await self.repo.update(ext)

    async def delete_extension(self, extension_id: int) -> None:
        await self.repo.delete(extension_id)
