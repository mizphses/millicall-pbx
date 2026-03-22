from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.database import get_session
from millicall.infrastructure.orm import devices_table, extensions_table, peers_table, trunks_table
from millicall.presentation.auth import get_current_user

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def get_dashboard(session: AsyncSession = Depends(get_session)):
    ext_count = (
        await session.execute(select(func.count()).select_from(extensions_table))
    ).scalar() or 0
    peer_count = (
        await session.execute(select(func.count()).select_from(peers_table))
    ).scalar() or 0
    trunk_count = (
        await session.execute(select(func.count()).select_from(trunks_table))
    ).scalar() or 0
    device_count = (
        await session.execute(select(func.count()).select_from(devices_table))
    ).scalar() or 0
    return {
        "extensions": ext_count,
        "peers": peer_count,
        "trunks": trunk_count,
        "devices": device_count,
    }
