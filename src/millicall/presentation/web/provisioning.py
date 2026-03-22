"""Provisioning endpoints for Panasonic KX-HDV phones."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.provisioning_service import ProvisioningService
from millicall.infrastructure.database import get_session

router = APIRouter(prefix="/provisioning", tags=["provisioning"])


@router.get("/Panasonic/ConfigCommon.cfg")
async def common_config(session: AsyncSession = Depends(get_session)):
    service = ProvisioningService(session)
    content = service.generate_common_config()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Panasonic/Config{mac_address}.cfg")
async def device_config(mac_address: str, session: AsyncSession = Depends(get_session)):
    service = ProvisioningService(session)
    content = await service.generate_device_config(mac_address)
    if content is None:
        return PlainTextResponse(
            "# Panasonic SIP Phone Standard Format File #\n# No configuration assigned\n",
            media_type="text/plain",
        )
    return PlainTextResponse(content, media_type="text/plain")
