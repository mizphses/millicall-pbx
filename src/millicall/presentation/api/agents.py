from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.ai_agent_service import AIAgentService
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user
from millicall.presentation.schemas import AgentCreate, AgentResponse, AgentUpdate

router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[AgentResponse])
async def list_agents(session: AsyncSession = Depends(get_session)):
    service = AIAgentService(session)
    agents = await service.list_agents()
    return [
        AgentResponse(
            id=a.id,
            name=a.name,
            extension_number=a.extension_number,
            system_prompt=a.system_prompt,
            greeting_text=a.greeting_text,
            coefont_voice_id=a.coefont_voice_id,
            tts_provider=a.tts_provider,
            google_tts_voice=a.google_tts_voice,
            llm_provider=a.llm_provider,
            llm_model=a.llm_model,
            max_history=a.max_history,
            enabled=a.enabled,
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, session: AsyncSession = Depends(get_session)):
    service = AIAgentService(session)
    a = await service.get_agent(agent_id)
    if not a:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return AgentResponse(
        id=a.id,
        name=a.name,
        extension_number=a.extension_number,
        system_prompt=a.system_prompt,
        greeting_text=a.greeting_text,
        coefont_voice_id=a.coefont_voice_id,
        tts_provider=a.tts_provider,
        google_tts_voice=a.google_tts_voice,
        llm_provider=a.llm_provider,
        llm_model=a.llm_model,
        max_history=a.max_history,
        enabled=a.enabled,
    )


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: AgentCreate,
    session: AsyncSession = Depends(get_session),
):
    service = AIAgentService(session)
    a = await service.create_agent(
        name=data.name,
        extension_number=data.extension_number,
        system_prompt=data.system_prompt,
        greeting_text=data.greeting_text,
        coefont_voice_id=data.coefont_voice_id,
        tts_provider=data.tts_provider,
        google_tts_voice=data.google_tts_voice,
        llm_provider=data.llm_provider,
        llm_model=data.llm_model,
        max_history=data.max_history,
        enabled=data.enabled,
    )
    return AgentResponse(
        id=a.id,
        name=a.name,
        extension_number=a.extension_number,
        system_prompt=a.system_prompt,
        greeting_text=a.greeting_text,
        coefont_voice_id=a.coefont_voice_id,
        tts_provider=a.tts_provider,
        google_tts_voice=a.google_tts_voice,
        llm_provider=a.llm_provider,
        llm_model=a.llm_model,
        max_history=a.max_history,
        enabled=a.enabled,
    )


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = AIAgentService(session)
    a = await service.update_agent(
        agent_id=agent_id,
        name=data.name,
        extension_number=data.extension_number,
        system_prompt=data.system_prompt,
        greeting_text=data.greeting_text,
        coefont_voice_id=data.coefont_voice_id,
        tts_provider=data.tts_provider,
        google_tts_voice=data.google_tts_voice,
        llm_provider=data.llm_provider,
        llm_model=data.llm_model,
        max_history=data.max_history,
        enabled=data.enabled,
    )
    return AgentResponse(
        id=a.id,
        name=a.name,
        extension_number=a.extension_number,
        system_prompt=a.system_prompt,
        greeting_text=a.greeting_text,
        coefont_voice_id=a.coefont_voice_id,
        tts_provider=a.tts_provider,
        google_tts_voice=a.google_tts_voice,
        llm_provider=a.llm_provider,
        llm_model=a.llm_model,
        max_history=a.max_history,
        enabled=a.enabled,
    )


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    service = AIAgentService(session)
    await service.delete_agent(agent_id)
