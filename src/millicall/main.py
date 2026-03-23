import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from millicall.config import settings
from millicall.domain.exceptions import (
    ContactNotFoundError,
    DuplicateExtensionError,
    DuplicatePeerError,
    DuplicateTrunkError,
    ExtensionNotFoundError,
    MillicallError,
    PeerNotFoundError,
    TrunkNotFoundError,
    WorkflowNotFoundError,
)
from millicall.infrastructure.database import engine
from millicall.infrastructure.orm import metadata
from millicall.presentation.api.agents import router as agents_api_router
from millicall.presentation.api.auth import router as auth_api_router
from millicall.presentation.api.call_history import router as call_history_api_router
from millicall.presentation.api.cdr import router as cdr_api_router
from millicall.presentation.api.dashboard import router as dashboard_api_router
from millicall.presentation.api.devices import router as devices_api_router
from millicall.presentation.api.extensions import router as extensions_api_router
from millicall.presentation.api.peers import router as peers_api_router
from millicall.presentation.api.settings import router as settings_api_router
from millicall.presentation.api.trunks import router as trunks_api_router
from millicall.presentation.api.users import router as users_api_router
from millicall.presentation.api.contacts import router as contacts_api_router
from millicall.presentation.api.workflows import router as workflows_api_router
from millicall.presentation.api.guide import router as guide_api_router
from millicall.presentation.web.provisioning import router as provisioning_router
from millicall.presentation.web.views import router as web_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _cdr_import_loop() -> None:
    from millicall.application.cdr_service import CDRService
    from millicall.infrastructure.database import async_session

    _csv_warned = False
    while True:
        try:
            async with async_session() as session:
                service = CDRService(session)
                if not service.CDR_CSV_PATH.exists() and not _csv_warned:
                    logger.warning(
                        "CDR CSV not found at %s — is cdr_csv module loaded?", service.CDR_CSV_PATH
                    )
                    _csv_warned = True
                count = await service.import_from_csv()
                if count > 0:
                    logger.info("Imported %d new CDR records", count)
                    _csv_warned = False
        except Exception:
            logger.exception("CDR import error")
        await asyncio.sleep(30)


async def _ensure_admin_user() -> None:
    """Create the default admin user if no users exist."""
    from millicall.domain.models import User
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.user_repo import UserRepository
    from millicall.presentation.auth import hash_password

    async with async_session() as session:
        repo = UserRepository(session)
        if await repo.count() == 0:
            hashed = hash_password(settings.admin_password)
            await repo.create(
                User(
                    username="admin",
                    hashed_password=hashed,
                    display_name="Administrator",
                    is_admin=True,
                )
            )
            logger.info("Created default admin user")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (fallback for dev without alembic)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    # Ensure default settings exist
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.settings_repo import SettingsRepository

    async with async_session() as session:
        repo = SettingsRepository(session)
        await repo.ensure_defaults()
    # Ensure default admin user exists
    await _ensure_admin_user()
    # Start CDR import background task
    cdr_task = asyncio.create_task(_cdr_import_loop())
    # Start MCP session manager if mounted
    mcp_cm = None
    if hasattr(app.state, "mcp_session_manager"):
        mcp_cm = app.state.mcp_session_manager.run()
        await mcp_cm.__aenter__()
    logger.info("Millicall PBX started")
    yield
    if mcp_cm:
        await mcp_cm.__aexit__(None, None, None)
    cdr_task.cancel()
    await engine.dispose()
    logger.info("Millicall PBX stopped")


app = FastAPI(
    title="Millicall PBX",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers — auth first (no auth required on login)
app.include_router(auth_api_router)
# Protected API routers (auth applied at router level)
app.include_router(extensions_api_router)
app.include_router(peers_api_router)
app.include_router(devices_api_router)
app.include_router(trunks_api_router)
app.include_router(agents_api_router)
app.include_router(settings_api_router)
app.include_router(call_history_api_router)
app.include_router(cdr_api_router)
app.include_router(dashboard_api_router)
app.include_router(workflows_api_router)
app.include_router(users_api_router)
app.include_router(contacts_api_router)
app.include_router(guide_api_router)

# Mount MCP server (Streamable HTTP at /mcp)
try:
    from millicall.mcp_server import get_streamable_http_app

    mcp_app = get_streamable_http_app()
    # Extract session manager for lifespan initialization
    for route in mcp_app.routes:
        handler = getattr(route, "app", None)
        if hasattr(handler, "session_manager"):
            app.state.mcp_session_manager = handler.session_manager
            break
    app.mount("/", mcp_app)
    logger.info("MCP server mounted at /mcp")
except Exception as e:
    logger.warning("Failed to mount MCP server: %s", e)

# Provisioning (no auth — devices need unauthenticated access)
app.include_router(provisioning_router)
# Web UI (backward compat)
app.include_router(web_router)


# Error handlers
@app.exception_handler(ExtensionNotFoundError)
@app.exception_handler(PeerNotFoundError)
@app.exception_handler(TrunkNotFoundError)
@app.exception_handler(WorkflowNotFoundError)
@app.exception_handler(ContactNotFoundError)
async def not_found_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DuplicateExtensionError)
@app.exception_handler(DuplicatePeerError)
@app.exception_handler(DuplicateTrunkError)
async def conflict_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
