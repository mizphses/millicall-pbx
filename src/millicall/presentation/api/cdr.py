from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.cdr_service import CDRService
from millicall.domain.models import User
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import CDRResponse

router = APIRouter(
    prefix="/api/cdr",
    tags=["cdr"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def list_cdr(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    service = CDRService(session)
    total = await service.count_records()
    records = await service.list_records(limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
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
        ],
    }


@router.post("/import")
async def import_cdr(
    session: AsyncSession = Depends(get_session), _admin: User = Depends(require_admin)
):
    service = CDRService(session)
    service.flush_cdr()
    csv_exists = service.CDR_CSV_PATH.exists()
    count = await service.import_from_csv()
    return {"imported": count, "csv_exists": csv_exists}
