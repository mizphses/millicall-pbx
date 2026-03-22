import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from millicall.domain.exceptions import (
    DuplicateExtensionError,
    DuplicatePeerError,
    DuplicateTrunkError,
    ExtensionNotFoundError,
    MillicallError,
    PeerNotFoundError,
    TrunkNotFoundError,
)
from millicall.infrastructure.database import engine
from millicall.infrastructure.orm import metadata
from millicall.presentation.api.devices import router as devices_api_router
from millicall.presentation.api.extensions import router as extensions_api_router
from millicall.presentation.api.peers import router as peers_api_router
from millicall.presentation.web.provisioning import router as provisioning_router
from millicall.presentation.web.views import router as web_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _cdr_import_loop() -> None:
    from millicall.application.cdr_service import CDRService
    from millicall.infrastructure.database import async_session
    while True:
        try:
            async with async_session() as session:
                service = CDRService(session)
                count = await service.import_from_csv()
                if count > 0:
                    logger.info("Imported %d new CDR records", count)
        except Exception:
            logger.exception("CDR import error")
        await asyncio.sleep(30)


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
    # Start CDR import background task
    cdr_task = asyncio.create_task(_cdr_import_loop())
    logger.info("Millicall PBX started")
    yield
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

# Include routers
app.include_router(extensions_api_router)
app.include_router(peers_api_router)
app.include_router(devices_api_router)
app.include_router(provisioning_router)
app.include_router(web_router)


# Error handlers
@app.exception_handler(ExtensionNotFoundError)
@app.exception_handler(PeerNotFoundError)
@app.exception_handler(TrunkNotFoundError)
async def not_found_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DuplicateExtensionError)
@app.exception_handler(DuplicatePeerError)
@app.exception_handler(DuplicateTrunkError)
async def conflict_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
