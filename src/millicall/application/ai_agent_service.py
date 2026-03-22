from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import AIAgent
from millicall.infrastructure.repositories.ai_agent_repo import AIAgentRepository


class AIAgentService:
    def __init__(self, session: AsyncSession):
        self.repo = AIAgentRepository(session)

    async def list_agents(self) -> list[AIAgent]:
        return await self.repo.get_all()

    async def get_agent(self, agent_id: int) -> AIAgent | None:
        return await self.repo.get_by_id(agent_id)

    async def get_agent_by_extension(self, extension_number: str) -> AIAgent | None:
        return await self.repo.get_by_extension(extension_number)

    async def create_agent(self, **kwargs) -> AIAgent:
        agent = AIAgent(**kwargs)
        return await self.repo.create(agent)

    async def update_agent(self, agent_id: int, **kwargs) -> AIAgent:
        agent = AIAgent(id=agent_id, **kwargs)
        return await self.repo.update(agent)

    async def delete_agent(self, agent_id: int) -> None:
        await self.repo.delete(agent_id)
