from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import AIAgent
from millicall.infrastructure.orm import ai_agents_table


class AIAgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> AIAgent:
        return AIAgent(
            id=row.id,
            name=row.name,
            extension_number=row.extension_number,
            system_prompt=row.system_prompt,
            greeting_text=row.greeting_text,
            coefont_voice_id=row.coefont_voice_id,
            tts_provider=row.tts_provider,
            google_tts_voice=row.google_tts_voice,
            llm_provider=row.llm_provider,
            llm_model=row.llm_model,
            max_history=row.max_history,
            enabled=row.enabled,
        )

    async def get_all(self) -> list[AIAgent]:
        result = await self.session.execute(
            select(ai_agents_table).order_by(ai_agents_table.c.extension_number)
        )
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, agent_id: int) -> AIAgent | None:
        result = await self.session.execute(
            select(ai_agents_table).where(ai_agents_table.c.id == agent_id)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def get_by_extension(self, extension_number: str) -> AIAgent | None:
        result = await self.session.execute(
            select(ai_agents_table).where(ai_agents_table.c.extension_number == extension_number)
        )
        row = result.first()
        return self._row_to_model(row) if row else None

    async def create(self, agent: AIAgent) -> AIAgent:
        result = await self.session.execute(
            ai_agents_table.insert().values(
                name=agent.name,
                extension_number=agent.extension_number,
                system_prompt=agent.system_prompt,
                greeting_text=agent.greeting_text,
                coefont_voice_id=agent.coefont_voice_id,
                tts_provider=agent.tts_provider,
                google_tts_voice=agent.google_tts_voice,
                llm_provider=agent.llm_provider,
                llm_model=agent.llm_model,
                max_history=agent.max_history,
                enabled=agent.enabled,
            )
        )
        await self.session.commit()
        agent.id = result.inserted_primary_key[0]
        return agent

    async def update(self, agent: AIAgent) -> AIAgent:
        await self.session.execute(
            update(ai_agents_table)
            .where(ai_agents_table.c.id == agent.id)
            .values(
                name=agent.name,
                extension_number=agent.extension_number,
                system_prompt=agent.system_prompt,
                greeting_text=agent.greeting_text,
                coefont_voice_id=agent.coefont_voice_id,
                tts_provider=agent.tts_provider,
                google_tts_voice=agent.google_tts_voice,
                llm_provider=agent.llm_provider,
                llm_model=agent.llm_model,
                max_history=agent.max_history,
                enabled=agent.enabled,
            )
        )
        await self.session.commit()
        return agent

    async def delete(self, agent_id: int) -> None:
        await self.session.execute(delete(ai_agents_table).where(ai_agents_table.c.id == agent_id))
        await self.session.commit()
