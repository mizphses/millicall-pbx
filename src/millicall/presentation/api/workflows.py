import json
import logging

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.workflow_service import WorkflowService
from millicall.domain.models import User
from millicall.domain.node_types import get_node_types_for_workflow_type
from millicall.infrastructure.database import get_session
from millicall.presentation.auth import get_current_user, require_admin
from millicall.presentation.schemas import (
    TTSConfig,
    WorkflowCreate,
    WorkflowDefinition,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowUpdate,
)

logger = logging.getLogger(__name__)

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
        default_tts_config=TTSConfig(**w.default_tts_config)
        if w.default_tts_config
        else TTSConfig(),
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
            extension_id=w.extension_id,
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


class GenerateRequest(BaseModel):
    prompt: str
    workflow_type: str = "ivr"


@router.post("/generate")
async def generate_workflow(data: GenerateRequest):
    """Use Gemini to generate a workflow definition from natural language."""
    from millicall.application.settings_service import SettingsService
    from millicall.infrastructure.database import async_session

    async with async_session() as session:
        svc = SettingsService(session)
        api_key = await svc.get_api_key("google")

    if not api_key:
        return {"error": "Google APIキーが設定されていません"}

    node_types = get_node_types_for_workflow_type(data.workflow_type)
    node_schema = json.dumps(
        {
            k: {
                "label": v["label"],
                "category": v["category"],
                "config_schema": {
                    ck: {
                        "type": cv.get("type"),
                        "label": cv.get("label"),
                        "default": cv.get("default"),
                    }
                    for ck, cv in v.get("config_schema", {}).items()
                },
            }
            for k, v in node_types.items()
        },
        ensure_ascii=False,
        indent=2,
    )

    system_prompt = f"""あなたはPBXワークフロー設計AIです。ユーザーの要件からワークフロー定義JSONを生成してください。

利用可能なノードタイプ:
{node_schema}

出力形式（厳密にこのJSON形式のみ出力。説明テキストは不要）:
{{
  "nodes": [
    {{"id": "node_1", "type": "start", "label": "開始", "position": {{"x": 0, "y": 0}}, "config": {{}}}},
    {{"id": "node_2", "type": "play_audio", "label": "挨拶", "position": {{"x": 0, "y": 120}}, "config": {{"tts_text": "お電話ありがとうございます"}}}}
  ],
  "edges": [
    {{"id": "e1", "source": "node_1", "target": "node_2", "sourceHandle": null, "label": null}}
  ]
}}

ルール:
- 必ず"start"ノードから始める
- 分岐ノード(condition, time_condition, api_call)のエッジにはsourceHandleを設定（"true"/"false", "match"/"no_match", "success"/"error"）
- ノードのpositionはy軸方向に120px間隔、分岐はx軸に200px間隔で配置
- configにはnode_typeのconfig_schemaに定義されたフィールドを使用
- JSONのみ出力。マークダウンやコードブロック記法は使わない"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": data.prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4000},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()

        text = result["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown code block if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        definition = json.loads(text)
        return {"definition": definition}
    except json.JSONDecodeError as e:
        logger.error("AI generated invalid JSON: %s", e)
        return {"error": "AIが有効なJSONを生成できませんでした", "raw": text}
    except Exception as e:
        logger.error("Workflow generation failed: %s", e)
        return {"error": str(e)}


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: int, session: AsyncSession = Depends(get_session)):
    service = WorkflowService(session)
    w = await service.get_workflow(workflow_id)
    return _to_response(w)


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    data: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    service = WorkflowService(session)
    w = await service.create_workflow(
        name=data.name,
        number=data.number,
        workflow_type=data.workflow_type,
        definition=data.definition.model_dump(),
        default_tts_config=data.default_tts_config.model_dump(),
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
    _admin: User = Depends(require_admin),
):
    service = WorkflowService(session)
    existing = await service.get_workflow(workflow_id)
    w = await service.update_workflow(
        workflow_id=workflow_id,
        name=data.name if data.name is not None else existing.name,
        number=data.number if data.number is not None else existing.number,
        workflow_type=data.workflow_type
        if data.workflow_type is not None
        else existing.workflow_type,
        definition=data.definition.model_dump()
        if data.definition is not None
        else existing.definition,
        default_tts_config=data.default_tts_config.model_dump()
        if data.default_tts_config is not None
        else existing.default_tts_config,
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
    _admin: User = Depends(require_admin),
):
    service = WorkflowService(session)
    await service.delete_workflow(workflow_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
