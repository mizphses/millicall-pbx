import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.exceptions import WorkflowNotFoundError
from millicall.domain.models import Workflow
from millicall.infrastructure.orm import workflows_table


class WorkflowRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _row_to_model(self, row) -> Workflow:
        definition = row.definition
        if isinstance(definition, str):
            definition = json.loads(definition)
        return Workflow(
            id=row.id,
            name=row.name,
            number=row.number,
            description=row.description,
            extension_id=row.extension_id,
            workflow_type=row.workflow_type,
            definition=definition,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_all(self) -> list[Workflow]:
        result = await self.session.execute(
            select(workflows_table).order_by(workflows_table.c.name)
        )
        return [self._row_to_model(row) for row in result]

    async def get_by_id(self, workflow_id: int) -> Workflow:
        result = await self.session.execute(
            select(workflows_table).where(workflows_table.c.id == workflow_id)
        )
        row = result.first()
        if not row:
            raise WorkflowNotFoundError(workflow_id)
        return self._row_to_model(row)

    async def get_by_number(self, number: str) -> Workflow | None:
        """Look up an enabled workflow by its extension number."""
        result = await self.session.execute(
            select(workflows_table)
            .where(workflows_table.c.number == number)
            .where(workflows_table.c.enabled == True)
        )
        row = result.first()
        if not row:
            return None
        return self._row_to_model(row)

    async def get_by_extension_id(self, extension_id: int) -> list[Workflow]:
        result = await self.session.execute(
            select(workflows_table)
            .where(workflows_table.c.extension_id == extension_id)
            .order_by(workflows_table.c.name)
        )
        return [self._row_to_model(row) for row in result]

    async def create(self, workflow: Workflow) -> Workflow:
        now = datetime.now()
        result = await self.session.execute(
            workflows_table.insert().values(
                name=workflow.name,
                number=workflow.number,
                description=workflow.description,
                extension_id=workflow.extension_id,
                workflow_type=workflow.workflow_type,
                definition=json.dumps(workflow.definition, ensure_ascii=False),
                enabled=workflow.enabled,
                created_at=now,
                updated_at=now,
            )
        )
        await self.session.commit()
        workflow.id = result.inserted_primary_key[0]
        workflow.created_at = now
        workflow.updated_at = now
        return workflow

    async def update(self, workflow: Workflow) -> Workflow:
        from sqlalchemy import update

        now = datetime.now()
        await self.session.execute(
            update(workflows_table)
            .where(workflows_table.c.id == workflow.id)
            .values(
                name=workflow.name,
                number=workflow.number,
                description=workflow.description,
                extension_id=workflow.extension_id,
                workflow_type=workflow.workflow_type,
                definition=json.dumps(workflow.definition, ensure_ascii=False),
                enabled=workflow.enabled,
                updated_at=now,
            )
        )
        await self.session.commit()
        workflow.updated_at = now
        return workflow

    async def delete(self, workflow_id: int) -> None:
        from sqlalchemy import delete

        await self.session.execute(
            delete(workflows_table).where(workflows_table.c.id == workflow_id)
        )
        await self.session.commit()
