from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.cdr_service import CDRService
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user
from millicall.presentation.schemas import CDRResponse

router = APIRouter(
    prefix="/api/cdr",
    tags=["cdr"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[CDRResponse])
async def list_cdr(
    limit: int = 200,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    service = CDRService(session)
    records = await service.list_records(limit=limit, offset=offset)
    return [
        CDRResponse(
            id=r.id,
            uniqueid=r.uniqueid,
            call_date=r.call_date,
            src=r.src,
            dst=r.dst,
            dcontext=r.dcontext,
            channel=r.channel,
            dst_channel=r.dst_channel,
            duration=r.duration,
            billsec=r.billsec,
            disposition=r.disposition,
        )
        for r in records
    ]


@router.post("/import")
async def import_cdr(session: AsyncSession = Depends(get_session)):
    service = CDRService(session)
    count = await service.import_from_csv()
    return {"imported": count}
