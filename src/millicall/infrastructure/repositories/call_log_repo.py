from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import CallLog, CallMessage
from millicall.infrastructure.orm import call_logs_table, call_messages_table


class CallLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_log(self, log: CallLog) -> int:
        result = await self.session.execute(
            call_logs_table.insert().values(
                agent_id=log.agent_id,
                agent_name=log.agent_name,
                extension_number=log.extension_number,
                caller_channel=log.caller_channel,
                started_at=log.started_at or datetime.now(),
                ended_at=log.ended_at,
                turn_count=log.turn_count,
            )
        )
        await self.session.commit()
        return result.inserted_primary_key[0]

    async def finish_log(self, log_id: int, turn_count: int) -> None:
        from sqlalchemy import update

        await self.session.execute(
            update(call_logs_table)
            .where(call_logs_table.c.id == log_id)
            .values(ended_at=datetime.now(), turn_count=turn_count)
        )
        await self.session.commit()

    async def add_message(self, msg: CallMessage) -> None:
        await self.session.execute(
            call_messages_table.insert().values(
                call_log_id=msg.call_log_id,
                role=msg.role,
                content=msg.content,
                turn=msg.turn,
                created_at=msg.created_at or datetime.now(),
            )
        )
        await self.session.commit()

    async def get_all_logs(self) -> list[CallLog]:
        result = await self.session.execute(
            select(call_logs_table).order_by(call_logs_table.c.started_at.desc())
        )
        return [
            CallLog(
                id=row.id,
                agent_id=row.agent_id,
                agent_name=row.agent_name,
                extension_number=row.extension_number,
                caller_channel=row.caller_channel,
                started_at=row.started_at,
                ended_at=row.ended_at,
                turn_count=row.turn_count,
            )
            for row in result
        ]

    async def get_log(self, log_id: int) -> CallLog | None:
        result = await self.session.execute(
            select(call_logs_table).where(call_logs_table.c.id == log_id)
        )
        row = result.first()
        if not row:
            return None
        return CallLog(
            id=row.id,
            agent_id=row.agent_id,
            agent_name=row.agent_name,
            extension_number=row.extension_number,
            caller_channel=row.caller_channel,
            started_at=row.started_at,
            ended_at=row.ended_at,
            turn_count=row.turn_count,
        )

    async def get_messages(self, log_id: int) -> list[CallMessage]:
        result = await self.session.execute(
            select(call_messages_table)
            .where(call_messages_table.c.call_log_id == log_id)
            .order_by(call_messages_table.c.turn, call_messages_table.c.id)
        )
        return [
            CallMessage(
                id=row.id,
                call_log_id=row.call_log_id,
                role=row.role,
                content=row.content,
                turn=row.turn,
                created_at=row.created_at,
            )
            for row in result
        ]

    async def delete_log(self, log_id: int) -> None:
        from sqlalchemy import delete

        await self.session.execute(
            delete(call_messages_table).where(call_messages_table.c.call_log_id == log_id)
        )
        await self.session.execute(delete(call_logs_table).where(call_logs_table.c.id == log_id))
        await self.session.commit()
