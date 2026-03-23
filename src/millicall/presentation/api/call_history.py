from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.call_log_repo import CallLogRepository
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import (
    CallLogDetailResponse,
    CallLogResponse,
    CallMessageResponse,
)

router = APIRouter(
    prefix="/api/call-history",
    tags=["call-history"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_call_logs(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    repo = CallLogRepository(session)
    total = await repo.count_logs()
    logs = await repo.get_all_logs(limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            CallLogResponse(
                id=log.id,
                agent_id=log.agent_id,
                agent_name=log.agent_name,
                extension_number=log.extension_number,
                caller_channel=log.caller_channel,
                started_at=log.started_at,
                ended_at=log.ended_at,
                turn_count=log.turn_count,
            )
            for log in logs
        ],
    }


@router.get("/{log_id}", response_model=CallLogDetailResponse)
async def get_call_log(log_id: int, session: AsyncSession = Depends(get_session)):
    repo = CallLogRepository(session)
    log = await repo.get_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail=f"Call log {log_id} not found")
    messages = await repo.get_messages(log_id)
    return CallLogDetailResponse(
        id=log.id,
        agent_id=log.agent_id,
        agent_name=log.agent_name,
        extension_number=log.extension_number,
        caller_channel=log.caller_channel,
        started_at=log.started_at,
        ended_at=log.ended_at,
        turn_count=log.turn_count,
        messages=[
            CallMessageResponse(
                id=m.id,
                call_log_id=m.call_log_id,
                role=m.role,
                content=m.content,
                turn=m.turn,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/{log_id}", status_code=204)
async def delete_call_log(
    log_id: int, session: AsyncSession = Depends(get_session), _admin: User = Depends(require_admin)
):
    repo = CallLogRepository(session)
    await repo.delete_log(log_id)
