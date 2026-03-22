import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from millicall.domain.exceptions import (
    DuplicateExtensionError,
    DuplicatePeerError,
    ExtensionNotFoundError,
    MillicallError,
    PeerNotFoundError,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (fallback for dev without alembic)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    logger.info("Millicall PBX started")
    yield
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
async def not_found_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(DuplicateExtensionError)
@app.exception_handler(DuplicatePeerError)
async def conflict_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
