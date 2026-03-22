from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.settings_service import SettingsService
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user
from millicall.presentation.schemas import SettingItem

router = APIRouter(
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[SettingItem])
async def list_settings(session: AsyncSession = Depends(get_session)):
    service = SettingsService(session)
    items = await service.get_all()
    return [
        SettingItem(key=item["key"], value=item["value"], description=item.get("description"))
        for item in items
    ]


@router.put("")
async def update_settings(
    items: list[SettingItem],
    session: AsyncSession = Depends(get_session),
):
    service = SettingsService(session)
    for item in items:
        await service.set(item.key, item.value)
    return {"status": "ok", "updated": len(items)}
