"""On-demand call API — manage and trigger one-click calls."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import OnDemandCall, User
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.ondemand_call_repo import OnDemandCallRepository
from millicall.presentation.auth import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ondemand-calls", tags=["ondemand-calls"])


class OnDemandCallCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=1, max_length=30)
    enabled: bool = True


class OnDemandCallResponse(BaseModel):
    id: int | None
    label: str
    phone_number: str
    enabled: bool


# --- Admin CRUD (requires auth) ---


@router.get("", response_model=list[OnDemandCallResponse], dependencies=[Depends(get_current_user)])
async def list_ondemand_calls(session: AsyncSession = Depends(get_session)):
    repo = OnDemandCallRepository(session)
    entries = await repo.get_all()
    return [OnDemandCallResponse(id=e.id, label=e.label, phone_number=e.phone_number, enabled=e.enabled) for e in entries]


@router.post("", response_model=OnDemandCallResponse, status_code=201)
async def create_ondemand_call(
    data: OnDemandCallCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = OnDemandCallRepository(session)
    entry = await repo.create(OnDemandCall(label=data.label, phone_number=data.phone_number, enabled=data.enabled))
    return OnDemandCallResponse(id=entry.id, label=entry.label, phone_number=entry.phone_number, enabled=entry.enabled)


@router.put("/{call_id}", response_model=OnDemandCallResponse)
async def update_ondemand_call(
    call_id: int,
    data: OnDemandCallCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = OnDemandCallRepository(session)
    existing = await repo.get_by_id(call_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.update(call_id, label=data.label, phone_number=data.phone_number, enabled=data.enabled)
    updated = await repo.get_by_id(call_id)
    assert updated is not None
    return OnDemandCallResponse(id=updated.id, label=updated.label, phone_number=updated.phone_number, enabled=updated.enabled)


@router.delete("/{call_id}", status_code=204)
async def delete_ondemand_call(
    call_id: int,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    repo = OnDemandCallRepository(session)
    existing = await repo.get_by_id(call_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Not found")
    await repo.delete(call_id)
