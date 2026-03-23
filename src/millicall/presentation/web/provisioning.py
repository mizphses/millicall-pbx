"""Provisioning endpoints for Panasonic KX-HDV and Yealink phones."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.provisioning_service import ProvisioningService
from millicall.infrastructure.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/provisioning", tags=["provisioning"])

# ── Panasonic KX-HDV ─────────────────────────────────────────────


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


# ── Yealink ──────────────────────────────────────────────────────


@router.get("/Yealink/y000000000000.boot")
async def yealink_boot(session: AsyncSession = Depends(get_session)):
    """Boot file — all Yealink models request this on startup."""
    service = ProvisioningService(session)
    content = service.generate_yealink_boot()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Yealink/{boot_file}.boot")
async def yealink_model_boot(boot_file: str, session: AsyncSession = Depends(get_session)):
    """Model-specific boot file (e.g. y000000000042 for T43U) — same content."""
    service = ProvisioningService(session)
    content = service.generate_yealink_boot()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Yealink/common.cfg")
async def yealink_common_config(session: AsyncSession = Depends(get_session)):
    """Common configuration shared by all Yealink phones."""
    service = ProvisioningService(session)
    content = service.generate_yealink_common_config()
    return PlainTextResponse(content, media_type="text/plain")


@router.get("/Yealink/{mac_address}.cfg")
async def yealink_device_config(
    mac_address: str, session: AsyncSession = Depends(get_session)
):
    """Per-device config — MAC address without separators (e.g. 805ec0a1b2c3.cfg)."""
    logger.info("Yealink provisioning request for MAC: %s", mac_address)
    service = ProvisioningService(session)
    content = await service.generate_yealink_device_config(mac_address)
    if content is None:
        return PlainTextResponse(
            "#!version:1.0.0.1\n## No configuration assigned\n",
            media_type="text/plain",
        )
    return PlainTextResponse(content, media_type="text/plain")
