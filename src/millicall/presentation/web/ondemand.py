"""On-demand call trigger — no auth required.

GET /ondemandcall/{id} — originates a call to the registered phone number.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.config import settings
from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.ondemand_call_repo import OnDemandCallRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ondemand-trigger"])


@router.get("/ondemandcall/{call_id}")
async def trigger_ondemand_call(call_id: int, session: AsyncSession = Depends(get_session)):
    """Trigger a call to the registered phone number. No authentication required."""
    repo = OnDemandCallRepository(session)
    entry = await repo.get_by_id(call_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    if not entry.enabled:
        raise HTTPException(status_code=403, detail="This call entry is disabled")

    # Originate via ARI using Local/ channel through [ondemand] dialplan context
    # The dialplan handles Dial() + Wait(3) + Hangup()
    ari_url = "http://localhost:8088/ari"
    api_key = f"{settings.ari_user}:{settings.ari_password}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{ari_url}/channels",
                params={
                    "endpoint": f"Local/{entry.phone_number}@ondemand",
                    "app": "millicall-mcp",
                    "api_key": api_key,
                },
            )

            if resp.status_code in (200, 201):
                channel_data = resp.json()
                channel_id = channel_data.get("id", "")
                logger.info(
                    "On-demand call triggered: id=%d number=%s channel=%s",
                    call_id,
                    entry.phone_number,
                    channel_id,
                )
                return JSONResponse({"ok": True, "number": entry.phone_number})

            logger.error("ARI originate failed: %d %s", resp.status_code, resp.text)
            raise HTTPException(status_code=502, detail="Failed to originate call")
    except httpx.HTTPError as e:
        logger.error("ARI connection error: %s", e)
        raise HTTPException(status_code=502, detail="PBX connection error") from e
