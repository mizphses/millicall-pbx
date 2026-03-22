from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.workflow_service import WorkflowService
from millicall.domain.node_types import get_node_types_for_workflow_type
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user
from millicall.presentation.schemas import (
    WorkflowCreate,
    WorkflowDefinition,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)

router = APIRouter(
    prefix="/api/workflows",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)],
)


def _to_response(w) -> WorkflowResponse:
    return WorkflowResponse(
        id=w.id,
        name=w.name,
        number=w.number,
        description=w.description,
        extension_id=w.extension_id,
        workflow_type=w.workflow_type,
        definition=WorkflowDefinition(**w.definition) if w.definition else WorkflowDefinition(),
        enabled=w.enabled,
        created_at=w.created_at,
        updated_at=w.updated_at,
    )


@router.get("", response_model=list[WorkflowListResponse])
async def list_workflows(session: AsyncSession = Depends(get_session)):
    service = WorkflowService(session)
    workflows = await service.list_workflows()
    return [
        WorkflowListResponse(
            id=w.id,
            name=w.name,
            number=w.number,
            description=w.description,
            workflow_type=w.workflow_type,
            enabled=w.enabled,
            node_count=len(w.definition.get("nodes", [])) if w.definition else 0,
            created_at=w.created_at,
            updated_at=w.updated_at,
        )
        for w in workflows
    ]


@router.get("/node-types")
async def get_node_types(workflow_type: str = Query(..., pattern=r"^(ivr|ai_workflow)$")):
    return get_node_types_for_workflow_type(workflow_type)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: int, session: AsyncSession = Depends(get_session)):
    service = WorkflowService(session)
    w = await service.get_workflow(workflow_id)
    return _to_response(w)


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
):
    service = WorkflowService(session)
    w = await service.create_workflow(
        name=data.name,
        number=data.number,
        workflow_type=data.workflow_type,
        definition=data.definition.model_dump(),
        description=data.description,
        enabled=data.enabled,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return _to_response(w)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: int,
    data: WorkflowUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = WorkflowService(session)
    existing = await service.get_workflow(workflow_id)
    w = await service.update_workflow(
        workflow_id=workflow_id,
        name=data.name if data.name is not None else existing.name,
        number=data.number if data.number is not None else existing.number,
        workflow_type=data.workflow_type if data.workflow_type is not None else existing.workflow_type,
        definition=data.definition.model_dump() if data.definition is not None else existing.definition,
        description=data.description if data.description is not None else existing.description,
        enabled=data.enabled if data.enabled is not None else existing.enabled,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return _to_response(w)


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: int,
    session: AsyncSession = Depends(get_session),
):
    service = WorkflowService(session)
    await service.delete_workflow(workflow_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
