import csv
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import CDR
from millicall.infrastructure.repositories.cdr_repo import CDRRepository

logger = logging.getLogger(__name__)

# Asterisk Master.csv column order:
# accountcode, src, dst, dcontext, clid, channel, dstchannel,
# lastapp, lastdata, start, answer, end, duration, billsec,
# disposition, amaflags, accountcode, uniqueid, userfield
COL_ACCOUNTCODE = 0
COL_SRC = 1
COL_DST = 2
COL_DCONTEXT = 3
COL_CLID = 4
COL_CHANNEL = 5
COL_DSTCHANNEL = 6
COL_START = 9
COL_DURATION = 12
COL_BILLSEC = 13
COL_DISPOSITION = 14
COL_UNIQUEID = 17
COL_USERFIELD = 18


class CDRService:
    CDR_CSV_PATH = Path("/var/log/asterisk/cdr-csv/Master.csv")

    def __init__(self, session: AsyncSession):
        self.repo = CDRRepository(session)

    async def import_from_csv(self) -> int:
        if not self.CDR_CSV_PATH.exists():
            return 0

        records: list[CDR] = []
        with open(self.CDR_CSV_PATH, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 18:
                    continue
                try:
                    call_date = datetime.strptime(row[COL_START], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                records.append(
                    CDR(
                        uniqueid=row[COL_UNIQUEID],
                        call_date=call_date,
                        clid=row[COL_CLID],
                        src=row[COL_SRC],
                        dst=row[COL_DST],
                        dcontext=row[COL_DCONTEXT],
                        channel=row[COL_CHANNEL],
                        dst_channel=row[COL_DSTCHANNEL],
                        duration=int(row[COL_DURATION] or 0),
                        billsec=int(row[COL_BILLSEC] or 0),
                        disposition=row[COL_DISPOSITION],
                        account_code=row[COL_ACCOUNTCODE],
                        userfield=row[COL_USERFIELD] if len(row) > COL_USERFIELD else "",
                    )
                )

        if not records:
            return 0

        return await self.repo.bulk_insert_ignore(records)

    async def list_records(self, limit: int = 200, offset: int = 0) -> list[CDR]:
        return await self.repo.get_all(limit=limit, offset=offset)

    async def count_records(self) -> int:
        return await self.repo.count()
