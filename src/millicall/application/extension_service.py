from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import AIAgent, Extension
from millicall.infrastructure.repositories.ai_agent_repo import AIAgentRepository
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository


class ExtensionService:
    def __init__(self, session: AsyncSession):
        self.repo = ExtensionRepository(session)
        self.agent_repo = AIAgentRepository(session)

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
        type: str = "phone",
        ai_agent_id: int | None = None,
    ) -> Extension:
        ext = Extension(
            number=number,
            display_name=display_name,
            enabled=enabled,
            peer_id=peer_id,
            type=type,
            ai_agent_id=ai_agent_id,
        )
        return await self.repo.create(ext)

    async def create_ai_extension(
        self,
        number: str,
        display_name: str,
        enabled: bool = True,
        **agent_kwargs,
    ) -> tuple[Extension, AIAgent]:
        """Create an AI agent and its corresponding extension."""
        agent = AIAgent(
            name=display_name,
            extension_number=number,
            enabled=enabled,
            **agent_kwargs,
        )
        agent = await self.agent_repo.create(agent)
        ext = Extension(
            number=number,
            display_name=display_name,
            enabled=enabled,
            type="ai_agent",
            ai_agent_id=agent.id,
        )
        ext = await self.repo.create(ext)
        return ext, agent

    async def update_extension(
        self,
        extension_id: int,
        number: str,
        display_name: str,
        enabled: bool = True,
        peer_id: int | None = None,
        type: str = "phone",
        ai_agent_id: int | None = None,
    ) -> Extension:
        ext = Extension(
            id=extension_id,
            number=number,
            display_name=display_name,
            enabled=enabled,
            peer_id=peer_id,
            type=type,
            ai_agent_id=ai_agent_id,
        )
        return await self.repo.update(ext)

    async def delete_extension(self, extension_id: int) -> None:
        ext = await self.repo.get_by_id(extension_id)
        if ext.type == "ai_agent" and ext.ai_agent_id:
            await self.agent_repo.delete(ext.ai_agent_id)
        await self.repo.delete(extension_id)
