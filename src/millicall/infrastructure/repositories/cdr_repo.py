from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import CDR
from millicall.infrastructure.orm import cdr_table


class CDRRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_insert_ignore(self, records: list[CDR]) -> int:
        if not records:
            return 0
        inserted = 0
        for record in records:
            result = await self.session.execute(
                text(
                    "INSERT OR IGNORE INTO cdr "
                    "(uniqueid, call_date, clid, src, dst, dcontext, channel, "
                    "dst_channel, duration, billsec, disposition, account_code, userfield) "
                    "VALUES (:uniqueid, :call_date, :clid, :src, :dst, :dcontext, :channel, "
                    ":dst_channel, :duration, :billsec, :disposition, :account_code, :userfield)"
                ),
                {
                    "uniqueid": record.uniqueid,
                    "call_date": record.call_date,
                    "clid": record.clid,
                    "src": record.src,
                    "dst": record.dst,
                    "dcontext": record.dcontext,
                    "channel": record.channel,
                    "dst_channel": record.dst_channel,
                    "duration": record.duration,
                    "billsec": record.billsec,
                    "disposition": record.disposition,
                    "account_code": record.account_code,
                    "userfield": record.userfield,
                },
            )
            inserted += result.rowcount
        await self.session.commit()
        return inserted

    async def get_all(self, limit: int = 200, offset: int = 0) -> list[CDR]:
        result = await self.session.execute(
            select(cdr_table)
            .order_by(cdr_table.c.call_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            CDR(
                id=row.id,
                uniqueid=row.uniqueid,
                call_date=row.call_date,
                clid=row.clid,
                src=row.src,
                dst=row.dst,
                dcontext=row.dcontext,
                channel=row.channel,
                dst_channel=row.dst_channel,
                duration=row.duration,
                billsec=row.billsec,
                disposition=row.disposition,
                account_code=row.account_code,
                userfield=row.userfield,
            )
            for row in result
        ]

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(cdr_table))
        return result.scalar() or 0
