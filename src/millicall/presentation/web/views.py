from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.ai_agent_service import AIAgentService
from millicall.application.asterisk_service import AsteriskService
from millicall.application.device_service import DeviceService
from millicall.application.extension_service import ExtensionService
from millicall.application.peer_service import PeerService
from millicall.application.settings_service import SettingsService
from millicall.application.trunk_service import TrunkService
from millicall.infrastructure.database import get_session

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    ext_service = ExtensionService(session)
    peer_service = PeerService(session)
    device_service = DeviceService(session)
    extensions = await ext_service.list_extensions()
    peers = await peer_service.list_peers()

    # Scan DHCP leases for connected devices
    await device_service.scan_dhcp_leases()
    devices = await device_service.list_devices()

    ext_map = {e.id: e for e in extensions}
    peer_map = {p.id: p for p in peers}

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "extensions": extensions,
            "peers": peers,
            "devices": devices,
            "ext_map": ext_map,
            "peer_map": peer_map,
        },
    )


# --- Extension views ---


@router.get("/extensions", response_class=HTMLResponse)
async def extensions_list(request: Request, session: AsyncSession = Depends(get_session)):
    ext_service = ExtensionService(session)
    peer_service = PeerService(session)
    extensions = await ext_service.list_extensions()
    peers = await peer_service.list_peers()
    peer_map = {p.id: p for p in peers}
    # Load agent info for AI extensions
    agent_service = AIAgentService(session)
    agent_map = {}
    for ext in extensions:
        if ext.type == "ai_agent" and ext.ai_agent_id:
            agent = await agent_service.get_agent(ext.ai_agent_id)
            if agent:
                agent_map[ext.ai_agent_id] = agent
    return templates.TemplateResponse(
        "extensions/list.html",
        {
            "request": request,
            "extensions": extensions,
            "peers": peers,
            "peer_map": peer_map,
            "agent_map": agent_map,
        },
    )


@router.get("/extensions/new", response_class=HTMLResponse)
async def extension_new_form(request: Request, session: AsyncSession = Depends(get_session)):
    peer_service = PeerService(session)
    peers = await peer_service.list_peers()
    return templates.TemplateResponse(
        "extensions/form.html",
        {
            "request": request,
            "extension": None,
            "agent": None,
            "peers": peers,
            "default_prompt": DEFAULT_AGENT_PROMPT,
        },
    )


@router.get("/extensions/{extension_id}/edit", response_class=HTMLResponse)
async def extension_edit_form(
    request: Request,
    extension_id: int,
    session: AsyncSession = Depends(get_session),
):
    ext_service = ExtensionService(session)
    peer_service = PeerService(session)
    extension = await ext_service.get_extension(extension_id)
    peers = await peer_service.list_peers()
    agent = None
    if extension.type == "ai_agent" and extension.ai_agent_id:
        agent_service = AIAgentService(session)
        agent = await agent_service.get_agent(extension.ai_agent_id)
    return templates.TemplateResponse(
        "extensions/form.html",
        {
            "request": request,
            "extension": extension,
            "agent": agent,
            "peers": peers,
            "default_prompt": DEFAULT_AGENT_PROMPT,
        },
    )


@router.post("/extensions", response_class=HTMLResponse)
async def extension_create(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    ext_type = form.get("type", "phone")
    number = form["number"]
    display_name = form["display_name"]
    enabled = form.get("enabled") == "true"

    ext_service = ExtensionService(session)

    if ext_type == "ai_agent":
        await ext_service.create_ai_extension(
            number=number,
            display_name=display_name,
            enabled=enabled,
            system_prompt=form.get("system_prompt", ""),
            greeting_text=form.get("greeting_text", "お電話ありがとうございます。ご用件をどうぞ。"),
            coefont_voice_id=form.get("coefont_voice_id", ""),
            tts_provider=form.get("tts_provider", "coefont"),
            google_tts_voice=form.get("google_tts_voice", "ja-JP-Chirp3-HD-Aoede"),
            llm_provider=form.get("llm_provider", "google"),
            llm_model=form.get("llm_model", "gemini-2.5-flash"),
            max_history=int(form.get("max_history", "10")),
        )
    else:
        peer_id = form.get("peer_id")
        await ext_service.create_extension(
            number=number,
            display_name=display_name,
            enabled=enabled,
            peer_id=int(peer_id) if peer_id else None,
            type="phone",
        )

    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/extensions", status_code=303)


@router.post("/extensions/{extension_id}", response_class=HTMLResponse)
async def extension_update(
    request: Request,
    extension_id: int,
    session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    ext_service = ExtensionService(session)
    extension = await ext_service.get_extension(extension_id)

    number = form["number"]
    display_name = form["display_name"]
    enabled = form.get("enabled") == "true"

    if extension.type == "ai_agent" and extension.ai_agent_id:
        # Update AI agent config
        agent_service = AIAgentService(session)
        await agent_service.update_agent(
            agent_id=extension.ai_agent_id,
            name=display_name,
            extension_number=number,
            system_prompt=form.get("system_prompt", ""),
            greeting_text=form.get("greeting_text", ""),
            coefont_voice_id=form.get("coefont_voice_id", ""),
            tts_provider=form.get("tts_provider", "coefont"),
            google_tts_voice=form.get("google_tts_voice", "ja-JP-Chirp3-HD-Aoede"),
            llm_provider=form.get("llm_provider", "google"),
            llm_model=form.get("llm_model", "gemini-2.5-flash"),
            max_history=int(form.get("max_history", "10")),
            enabled=enabled,
        )
        await ext_service.update_extension(
            extension_id=extension_id,
            number=number,
            display_name=display_name,
            enabled=enabled,
            type="ai_agent",
            ai_agent_id=extension.ai_agent_id,
        )
    else:
        peer_id = form.get("peer_id")
        await ext_service.update_extension(
            extension_id=extension_id,
            number=number,
            display_name=display_name,
            enabled=enabled,
            peer_id=int(peer_id) if peer_id else None,
            type="phone",
        )

    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/extensions", status_code=303)


@router.post("/extensions/{extension_id}/delete", response_class=HTMLResponse)
async def extension_delete(
    extension_id: int,
    session: AsyncSession = Depends(get_session),
):
    ext_service = ExtensionService(session)
    await ext_service.delete_extension(extension_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/extensions", status_code=303)


# --- Peer views ---


@router.get("/peers", response_class=HTMLResponse)
async def peers_list(request: Request, session: AsyncSession = Depends(get_session)):
    peer_service = PeerService(session)
    peers = await peer_service.list_peers()
    return templates.TemplateResponse(
        "peers/list.html",
        {
            "request": request,
            "peers": peers,
        },
    )


@router.get("/peers/new", response_class=HTMLResponse)
async def peer_new_form(request: Request):
    return templates.TemplateResponse(
        "peers/form.html",
        {
            "request": request,
            "peer": None,
        },
    )


@router.get("/peers/{peer_id}/edit", response_class=HTMLResponse)
async def peer_edit_form(
    request: Request,
    peer_id: int,
    session: AsyncSession = Depends(get_session),
):
    peer_service = PeerService(session)
    peer = await peer_service.get_peer(peer_id)
    return templates.TemplateResponse(
        "peers/form.html",
        {
            "request": request,
            "peer": peer,
        },
    )


@router.post("/peers", response_class=HTMLResponse)
async def peer_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    transport: str = Form(default="udp"),
    codecs: str = Form(default="ulaw,alaw"),
    ip_address: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
):
    peer_service = PeerService(session)
    await peer_service.create_peer(
        username=username,
        password=password,
        transport=transport,
        codecs=[c.strip() for c in codecs.split(",") if c.strip()],
        ip_address=ip_address or None,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/peers", status_code=303)


@router.post("/peers/{peer_id}", response_class=HTMLResponse)
async def peer_update(
    request: Request,
    peer_id: int,
    username: str = Form(...),
    password: str = Form(...),
    transport: str = Form(default="udp"),
    codecs: str = Form(default="ulaw,alaw"),
    ip_address: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
):
    peer_service = PeerService(session)
    await peer_service.update_peer(
        peer_id=peer_id,
        username=username,
        password=password,
        transport=transport,
        codecs=[c.strip() for c in codecs.split(",") if c.strip()],
        ip_address=ip_address or None,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/peers", status_code=303)


@router.post("/peers/{peer_id}/delete", response_class=HTMLResponse)
async def peer_delete(
    peer_id: int,
    session: AsyncSession = Depends(get_session),
):
    peer_service = PeerService(session)
    await peer_service.delete_peer(peer_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/peers", status_code=303)


# --- Device views ---


@router.get("/devices", response_class=HTMLResponse)
async def devices_list(request: Request, session: AsyncSession = Depends(get_session)):
    device_service = DeviceService(session)
    ext_service = ExtensionService(session)
    peer_service = PeerService(session)
    await device_service.scan_dhcp_leases()
    devices = await device_service.list_devices()
    extensions = await ext_service.list_extensions()
    peers = await peer_service.list_peers()
    ext_map = {e.id: e for e in extensions}
    peer_map = {p.id: p for p in peers}
    return templates.TemplateResponse(
        "devices/list.html",
        {
            "request": request,
            "devices": devices,
            "ext_map": ext_map,
            "peer_map": peer_map,
        },
    )


@router.post("/devices/scan", response_class=HTMLResponse)
async def devices_scan(session: AsyncSession = Depends(get_session)):
    device_service = DeviceService(session)
    await device_service.scan_dhcp_leases()
    return RedirectResponse(url="/devices", status_code=303)


@router.get("/devices/{device_id}/provision", response_class=HTMLResponse)
async def device_provision_form(
    request: Request,
    device_id: int,
    session: AsyncSession = Depends(get_session),
):
    device_service = DeviceService(session)
    ext_service = ExtensionService(session)
    peer_service = PeerService(session)
    device = await device_service.get_device(device_id)
    extensions = await ext_service.list_extensions()
    peers = await peer_service.list_peers()
    return templates.TemplateResponse(
        "devices/provision.html",
        {
            "request": request,
            "device": device,
            "extensions": extensions,
            "peers": peers,
        },
    )


@router.post("/devices/{device_id}/auto-provision", response_class=HTMLResponse)
async def device_auto_provision(
    device_id: int,
    extension_number: str = Form(...),
    display_name: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    device_service = DeviceService(session)
    await device_service.auto_provision(device_id, extension_number, display_name)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/devices", status_code=303)


@router.post("/devices/{device_id}/assign", response_class=HTMLResponse)
async def device_assign(
    device_id: int,
    peer_id: int | None = Form(default=None),
    extension_id: int | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    device_service = DeviceService(session)
    await device_service.assign_device(
        device_id,
        peer_id if peer_id else None,
        extension_id if extension_id else None,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/devices", status_code=303)


@router.post("/devices/{device_id}/delete", response_class=HTMLResponse)
async def device_delete(
    device_id: int,
    session: AsyncSession = Depends(get_session),
):
    device_service = DeviceService(session)
    device = await device_service.get_device(device_id)
    if device:
        await device_service.device_repo.delete(device_id)
    return RedirectResponse(url="/devices", status_code=303)


# --- AI Agent views ---

DEFAULT_AGENT_PROMPT = """あなたは電話応対AIアシスタントです。
丁寧な敬語で応対してください。
回答は3文以内で簡潔にしてください。
分からないことは正直に「担当者に確認いたします」と答えてください。"""


@router.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request, session: AsyncSession = Depends(get_session)):
    agent_service = AIAgentService(session)
    agents = await agent_service.list_agents()
    return templates.TemplateResponse(
        "agents/list.html",
        {
            "request": request,
            "agents": agents,
        },
    )


@router.get("/agents/new", response_class=HTMLResponse)
async def agent_new_form(request: Request):
    return templates.TemplateResponse(
        "agents/form.html",
        {
            "request": request,
            "agent": None,
            "default_prompt": DEFAULT_AGENT_PROMPT,
        },
    )


@router.get("/agents/{agent_id}/edit", response_class=HTMLResponse)
async def agent_edit_form(
    request: Request,
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    agent_service = AIAgentService(session)
    agent = await agent_service.get_agent(agent_id)
    return templates.TemplateResponse(
        "agents/form.html",
        {
            "request": request,
            "agent": agent,
            "default_prompt": DEFAULT_AGENT_PROMPT,
        },
    )


@router.post("/agents", response_class=HTMLResponse)
async def agent_create(
    request: Request,
    name: str = Form(...),
    extension_number: str = Form(...),
    system_prompt: str = Form(...),
    greeting_text: str = Form(...),
    coefont_voice_id: str = Form(default=""),
    tts_provider: str = Form(default="coefont"),
    google_tts_voice: str = Form(default="ja-JP-Chirp3-HD-Aoede"),
    llm_provider: str = Form(default="google"),
    llm_model: str = Form(default="gemini-2.5-flash"),
    max_history: int = Form(default=10),
    enabled: bool = Form(default=False),
    session: AsyncSession = Depends(get_session),
):
    agent_service = AIAgentService(session)
    await agent_service.create_agent(
        name=name,
        extension_number=extension_number,
        system_prompt=system_prompt,
        greeting_text=greeting_text,
        coefont_voice_id=coefont_voice_id,
        tts_provider=tts_provider,
        google_tts_voice=google_tts_voice,
        llm_provider=llm_provider,
        llm_model=llm_model,
        max_history=max_history,
        enabled=enabled,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/agents", status_code=303)


@router.post("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_update(
    agent_id: int,
    name: str = Form(...),
    extension_number: str = Form(...),
    system_prompt: str = Form(...),
    greeting_text: str = Form(...),
    coefont_voice_id: str = Form(default=""),
    tts_provider: str = Form(default="coefont"),
    google_tts_voice: str = Form(default="ja-JP-Chirp3-HD-Aoede"),
    llm_provider: str = Form(default="google"),
    llm_model: str = Form(default="gemini-2.5-flash"),
    max_history: int = Form(default=10),
    enabled: bool = Form(default=False),
    session: AsyncSession = Depends(get_session),
):
    agent_service = AIAgentService(session)
    await agent_service.update_agent(
        agent_id=agent_id,
        name=name,
        extension_number=extension_number,
        system_prompt=system_prompt,
        greeting_text=greeting_text,
        coefont_voice_id=coefont_voice_id,
        tts_provider=tts_provider,
        google_tts_voice=google_tts_voice,
        llm_provider=llm_provider,
        llm_model=llm_model,
        max_history=max_history,
        enabled=enabled,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/agents", status_code=303)


@router.post("/agents/{agent_id}/delete", response_class=HTMLResponse)
async def agent_delete(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    agent_service = AIAgentService(session)
    await agent_service.delete_agent(agent_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/agents", status_code=303)


# --- Trunk views ---


@router.get("/trunks", response_class=HTMLResponse)
async def trunks_list(request: Request, session: AsyncSession = Depends(get_session)):
    trunk_service = TrunkService(session)
    trunks = await trunk_service.list_trunks()
    return templates.TemplateResponse(
        "trunks/list.html",
        {
            "request": request,
            "trunks": trunks,
        },
    )


@router.get("/trunks/new", response_class=HTMLResponse)
async def trunk_new_form(request: Request):
    return templates.TemplateResponse(
        "trunks/form.html",
        {
            "request": request,
            "trunk": None,
        },
    )


@router.get("/trunks/{trunk_id}/edit", response_class=HTMLResponse)
async def trunk_edit_form(
    request: Request,
    trunk_id: int,
    session: AsyncSession = Depends(get_session),
):
    trunk_service = TrunkService(session)
    trunk = await trunk_service.get_trunk(trunk_id)
    return templates.TemplateResponse(
        "trunks/form.html",
        {
            "request": request,
            "trunk": trunk,
        },
    )


@router.post("/trunks", response_class=HTMLResponse)
async def trunk_create(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    trunk_service = TrunkService(session)
    did_number = form.get("did_number", "")
    await trunk_service.create_trunk(
        name=form["name"],
        display_name=form["display_name"],
        host=form["host"],
        username=form["username"],
        password=form["password"],
        did_number=did_number,
        caller_id=did_number,
        incoming_dest=form.get("incoming_dest", ""),
        outbound_prefixes=form.get("outbound_prefixes", ""),
        enabled=form.get("enabled") == "true",
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/trunks", status_code=303)


@router.post("/trunks/{trunk_id}", response_class=HTMLResponse)
async def trunk_update(
    request: Request,
    trunk_id: int,
    session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    trunk_service = TrunkService(session)
    did_number = form.get("did_number", "")
    await trunk_service.update_trunk(
        trunk_id=trunk_id,
        name=form["name"],
        display_name=form["display_name"],
        host=form["host"],
        username=form["username"],
        password=form["password"],
        did_number=did_number,
        caller_id=did_number,
        incoming_dest=form.get("incoming_dest", ""),
        outbound_prefixes=form.get("outbound_prefixes", ""),
        enabled=form.get("enabled") == "true",
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/trunks", status_code=303)


@router.post("/trunks/{trunk_id}/delete", response_class=HTMLResponse)
async def trunk_delete(
    trunk_id: int,
    session: AsyncSession = Depends(get_session),
):
    trunk_service = TrunkService(session)
    await trunk_service.delete_trunk(trunk_id)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/trunks", status_code=303)


# --- Settings views ---


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    from millicall.infrastructure.repositories.settings_repo import SettingsRepository

    repo = SettingsRepository(session)
    await repo.ensure_defaults()
    settings_svc = SettingsService(session)
    settings_list = await settings_svc.get_all()
    settings_dict = {s["key"]: s["value"] for s in settings_list}
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings_list": settings_list,
            "s": settings_dict,
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    settings_svc = SettingsService(session)
    for key, value in form.items():
        await settings_svc.set(key, value)
    # Regenerate Asterisk config (trunk settings may have changed)
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/settings", status_code=303)


# --- Call History views ---


@router.get("/call-history", response_class=HTMLResponse)
async def call_history_list(request: Request, session: AsyncSession = Depends(get_session)):
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    repo = CallLogRepository(session)
    logs = await repo.get_all_logs()
    return templates.TemplateResponse(
        "call_history/list.html",
        {
            "request": request,
            "logs": logs,
        },
    )


@router.get("/call-history/{log_id}", response_class=HTMLResponse)
async def call_history_detail(
    request: Request,
    log_id: int,
    session: AsyncSession = Depends(get_session),
):
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    repo = CallLogRepository(session)
    log = await repo.get_log(log_id)
    messages = await repo.get_messages(log_id) if log else []
    return templates.TemplateResponse(
        "call_history/detail.html",
        {
            "request": request,
            "log": log,
            "messages": messages,
        },
    )


@router.post("/call-history/{log_id}/delete", response_class=HTMLResponse)
async def call_history_delete(
    log_id: int,
    session: AsyncSession = Depends(get_session),
):
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    repo = CallLogRepository(session)
    await repo.delete_log(log_id)
    return RedirectResponse(url="/call-history", status_code=303)


# --- CDR views ---


@router.get("/cdr", response_class=HTMLResponse)
async def cdr_list(request: Request, session: AsyncSession = Depends(get_session)):
    from millicall.application.cdr_service import CDRService

    service = CDRService(session)
    records = await service.list_records(limit=200)
    total = await service.count_records()
    return templates.TemplateResponse(
        "cdr/list.html",
        {
            "request": request,
            "records": records,
            "total": total,
        },
    )


@router.post("/cdr/import", response_class=HTMLResponse)
async def cdr_manual_import(session: AsyncSession = Depends(get_session)):
    from millicall.application.cdr_service import CDRService

    service = CDRService(session)
    await service.import_from_csv()
    return RedirectResponse(url="/cdr", status_code=303)


# --- Call History JSON API ---


@router.get("/api/call-history")
async def api_call_history(session: AsyncSession = Depends(get_session)):
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    repo = CallLogRepository(session)
    logs = await repo.get_all_logs()
    result = []
    for log in logs:
        messages = await repo.get_messages(log.id)
        result.append(
            {
                "id": log.id,
                "agent_name": log.agent_name,
                "extension_number": log.extension_number,
                "caller_channel": log.caller_channel,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "ended_at": log.ended_at.isoformat() if log.ended_at else None,
                "turn_count": log.turn_count,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "turn": m.turn,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in messages
                ],
            }
        )
    return JSONResponse(content=result)


@router.get("/api/cdr")
async def api_cdr_list(session: AsyncSession = Depends(get_session)):
    from millicall.application.cdr_service import CDRService

    service = CDRService(session)
    records = await service.list_records(limit=500)
    return JSONResponse(
        content=[
            {
                "id": r.id,
                "uniqueid": r.uniqueid,
                "call_date": r.call_date.isoformat() if r.call_date else None,
                "src": r.src,
                "dst": r.dst,
                "dcontext": r.dcontext,
                "channel": r.channel,
                "dst_channel": r.dst_channel,
                "duration": r.duration,
                "billsec": r.billsec,
                "disposition": r.disposition,
            }
            for r in records
        ]
    )


@router.get("/api/call-history/{log_id}")
async def api_call_history_detail(log_id: int, session: AsyncSession = Depends(get_session)):
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    repo = CallLogRepository(session)
    log = await repo.get_log(log_id)
    if not log:
        return JSONResponse(content={"error": "not found"}, status_code=404)
    messages = await repo.get_messages(log_id)
    return JSONResponse(
        content={
            "id": log.id,
            "agent_name": log.agent_name,
            "extension_number": log.extension_number,
            "caller_channel": log.caller_channel,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "ended_at": log.ended_at.isoformat() if log.ended_at else None,
            "turn_count": log.turn_count,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "turn": m.turn,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }
    )
