from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.application.asterisk_service import AsteriskService
from millicall.application.device_service import DeviceService
from millicall.application.extension_service import ExtensionService
from millicall.application.peer_service import PeerService
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

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "extensions": extensions,
        "peers": peers,
        "devices": devices,
        "ext_map": ext_map,
        "peer_map": peer_map,
    })


# --- Extension views ---

@router.get("/extensions", response_class=HTMLResponse)
async def extensions_list(request: Request, session: AsyncSession = Depends(get_session)):
    ext_service = ExtensionService(session)
    peer_service = PeerService(session)
    extensions = await ext_service.list_extensions()
    peers = await peer_service.list_peers()
    peer_map = {p.id: p for p in peers}
    return templates.TemplateResponse("extensions/list.html", {
        "request": request,
        "extensions": extensions,
        "peers": peers,
        "peer_map": peer_map,
    })


@router.get("/extensions/new", response_class=HTMLResponse)
async def extension_new_form(request: Request, session: AsyncSession = Depends(get_session)):
    peer_service = PeerService(session)
    peers = await peer_service.list_peers()
    return templates.TemplateResponse("extensions/form.html", {
        "request": request,
        "extension": None,
        "peers": peers,
    })


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
    return templates.TemplateResponse("extensions/form.html", {
        "request": request,
        "extension": extension,
        "peers": peers,
    })


@router.post("/extensions", response_class=HTMLResponse)
async def extension_create(
    request: Request,
    number: str = Form(...),
    display_name: str = Form(...),
    enabled: bool = Form(default=False),
    peer_id: int | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    ext_service = ExtensionService(session)
    await ext_service.create_extension(
        number=number,
        display_name=display_name,
        enabled=enabled,
        peer_id=peer_id if peer_id else None,
    )
    asterisk = AsteriskService(session)
    await asterisk.apply_config()
    return RedirectResponse(url="/extensions", status_code=303)


@router.post("/extensions/{extension_id}", response_class=HTMLResponse)
async def extension_update(
    request: Request,
    extension_id: int,
    number: str = Form(...),
    display_name: str = Form(...),
    enabled: bool = Form(default=False),
    peer_id: int | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    ext_service = ExtensionService(session)
    await ext_service.update_extension(
        extension_id=extension_id,
        number=number,
        display_name=display_name,
        enabled=enabled,
        peer_id=peer_id if peer_id else None,
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
    ext_service = ExtensionService(session)
    peers = await peer_service.list_peers()
    extensions = await ext_service.list_extensions()
    ext_map = {e.id: e for e in extensions}
    return templates.TemplateResponse("peers/list.html", {
        "request": request,
        "peers": peers,
        "extensions": extensions,
        "ext_map": ext_map,
    })


@router.get("/peers/new", response_class=HTMLResponse)
async def peer_new_form(request: Request, session: AsyncSession = Depends(get_session)):
    ext_service = ExtensionService(session)
    extensions = await ext_service.list_extensions()
    return templates.TemplateResponse("peers/form.html", {
        "request": request,
        "peer": None,
        "extensions": extensions,
    })


@router.get("/peers/{peer_id}/edit", response_class=HTMLResponse)
async def peer_edit_form(
    request: Request,
    peer_id: int,
    session: AsyncSession = Depends(get_session),
):
    peer_service = PeerService(session)
    ext_service = ExtensionService(session)
    peer = await peer_service.get_peer(peer_id)
    extensions = await ext_service.list_extensions()
    return templates.TemplateResponse("peers/form.html", {
        "request": request,
        "peer": peer,
        "extensions": extensions,
    })


@router.post("/peers", response_class=HTMLResponse)
async def peer_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    transport: str = Form(default="udp"),
    codecs: str = Form(default="ulaw,alaw"),
    ip_address: str = Form(default=""),
    extension_id: int | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
):
    peer_service = PeerService(session)
    await peer_service.create_peer(
        username=username,
        password=password,
        transport=transport,
        codecs=[c.strip() for c in codecs.split(",") if c.strip()],
        ip_address=ip_address or None,
        extension_id=extension_id if extension_id else None,
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
    extension_id: int | None = Form(default=None),
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
        extension_id=extension_id if extension_id else None,
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
    return templates.TemplateResponse("devices/provision.html", {
        "request": request,
        "device": device,
        "extensions": extensions,
        "peers": peers,
    })


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
    return RedirectResponse(url="/", status_code=303)


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
    return RedirectResponse(url="/", status_code=303)


@router.post("/devices/{device_id}/delete", response_class=HTMLResponse)
async def device_delete(
    device_id: int,
    session: AsyncSession = Depends(get_session),
):
    device_service = DeviceService(session)
    device = await device_service.get_device(device_id)
    if device:
        await device_service.device_repo.delete(device_id)
    return RedirectResponse(url="/", status_code=303)
