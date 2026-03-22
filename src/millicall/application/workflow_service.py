from sqlalchemy.ext.asyncio import AsyncSession

from millicall.domain.models import Extension, Workflow
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.workflow_repo import WorkflowRepository


class WorkflowService:
    def __init__(self, session: AsyncSession):
        self.repo = WorkflowRepository(session)
        self.ext_repo = ExtensionRepository(session)

    async def list_workflows(self) -> list[Workflow]:
        return await self.repo.get_all()

    async def get_workflow(self, workflow_id: int) -> Workflow:
        return await self.repo.get_by_id(workflow_id)

    async def create_workflow(
        self,
        name: str,
        number: str,
        workflow_type: str,
        definition: dict | None = None,
        default_tts_config: dict | None = None,
        description: str = "",
        enabled: bool = True,
    ) -> Workflow:
        # Auto-create extension for this workflow
        ext = Extension(
            number=number,
            display_name=name,
            enabled=enabled,
            type=workflow_type,
        )
        ext = await self.ext_repo.create(ext)

        workflow = Workflow(
            name=name,
            number=number,
            workflow_type=workflow_type,
            definition=definition or {},
            default_tts_config=default_tts_config or {},
            extension_id=ext.id,
            description=description,
            enabled=enabled,
        )
        return await self.repo.create(workflow)

    async def update_workflow(
        self,
        workflow_id: int,
        name: str,
        number: str,
        workflow_type: str,
        definition: dict,
        default_tts_config: dict | None = None,
        description: str = "",
        enabled: bool = True,
    ) -> Workflow:
        existing = await self.repo.get_by_id(workflow_id)

        # Update associated extension
        if existing.extension_id:
            ext = await self.ext_repo.get_by_id(existing.extension_id)
            ext.number = number
            ext.display_name = name
            ext.enabled = enabled
            ext.type = workflow_type
            await self.ext_repo.update(ext)

        workflow = Workflow(
            id=workflow_id,
            name=name,
            number=number,
            workflow_type=workflow_type,
            definition=definition,
            default_tts_config=default_tts_config or existing.default_tts_config or {},
            extension_id=existing.extension_id,
            description=description,
            enabled=enabled,
        )
        return await self.repo.update(workflow)

    async def delete_workflow(self, workflow_id: int) -> None:
        existing = await self.repo.get_by_id(workflow_id)
        # Delete associated extension
        if existing.extension_id:
            await self.ext_repo.delete(existing.extension_id)
        await self.repo.delete(workflow_id)
