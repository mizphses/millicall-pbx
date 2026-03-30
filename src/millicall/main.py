import asyncio
import logging
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from millicall.config import settings
from millicall.domain.exceptions import (
    ContactNotFoundError,
    DuplicateExtensionError,
    DuplicatePeerError,
    DuplicateTrunkError,
    DuplicateWorkflowNumberError,
    ExtensionNotFoundError,
    MillicallError,
    PeerNotFoundError,
    TrunkNotFoundError,
    WorkflowNotFoundError,
)
from millicall.domain.models import User
from millicall.infrastructure.database import engine
from millicall.infrastructure.orm import metadata
from millicall.presentation.api.agents import router as agents_api_router
from millicall.presentation.api.auth import router as auth_api_router
from millicall.presentation.api.call_history import router as call_history_api_router
from millicall.presentation.api.cdr import router as cdr_api_router
from millicall.presentation.api.contacts import router as contacts_api_router
from millicall.presentation.api.dashboard import router as dashboard_api_router
from millicall.presentation.api.devices import router as devices_api_router
from millicall.presentation.api.extensions import router as extensions_api_router
from millicall.presentation.api.guide import router as guide_api_router
from millicall.presentation.api.ondemand_calls import router as ondemand_calls_api_router
from millicall.presentation.api.peers import router as peers_api_router
from millicall.presentation.api.settings import router as settings_api_router
from millicall.presentation.api.trunks import router as trunks_api_router
from millicall.presentation.api.users import router as users_api_router
from millicall.presentation.api.wireguard import router as wireguard_api_router
from millicall.presentation.api.workflows import router as workflows_api_router
from millicall.presentation.web.ondemand import router as ondemand_trigger_router
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
    # Start LDAP server for phone directory
    try:
        from millicall.infrastructure.ldap_server import start_ldap_server

        start_ldap_server(port=10389)
    except Exception:
        logger.warning("LDAP server failed to start", exc_info=True)
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
app.include_router(ondemand_calls_api_router)
app.include_router(wireguard_api_router)

# No-auth endpoints — must be before MCP mount which catches all routes under "/"
app.include_router(provisioning_router)
app.include_router(ondemand_trigger_router)


# ---------------------------------------------------------------------------
# MCP OAuth login page
# ---------------------------------------------------------------------------
@app.get("/mcp-login", response_class=HTMLResponse)
async def mcp_login_page(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    code_challenge: str = Query(...),
    state: str = Query(""),
    scopes: str = Query(""),
):
    """Show login form for MCP OAuth authorization."""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Millicall PBX - MCP認証</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: "Noto Sans JP", sans-serif;
    background: #f0eeeb;
    color: #1b1b1f;
    -webkit-font-smoothing: antialiased;
    display: flex;
    justify-content: center;
    min-height: 100vh;
    padding-top: 80px;
  }}
  .container {{
    width: 100%;
    max-width: 400px;
    padding: 0 16px;
  }}
  h1 {{
    font-size: 21px;
    font-weight: 700;
    margin-bottom: 4px;
  }}
  .subtitle {{
    font-size: 13px;
    color: #4a4a52;
    margin-bottom: 24px;
  }}
  .card {{
    background: #ffffff;
    border: 1px solid #d4d2cd;
    border-radius: 5px;
    padding: 20px;
  }}
  .form-group {{
    margin-bottom: 16px;
  }}
  label {{
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #1b1b1f;
    margin-bottom: 6px;
  }}
  input[type="text"],
  input[type="password"] {{
    width: 100%;
    padding: 8px 10px;
    font-size: 14px;
    font-family: "Noto Sans JP", sans-serif;
    color: #1b1b1f;
    background: #ffffff;
    border: 1px solid #d4d2cd;
    border-radius: 5px;
    min-height: 38px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
  }}
  input[type="text"]:focus,
  input[type="password"]:focus {{
    border-color: #c45d2c;
    box-shadow: 0 0 0 2px rgba(196, 93, 44, 0.12);
  }}
  button {{
    width: 100%;
    padding: 10px 18px;
    font-size: 14px;
    font-weight: 500;
    font-family: "Noto Sans JP", sans-serif;
    border: none;
    border-radius: 5px;
    background: #c45d2c;
    color: #ffffff;
    min-height: 38px;
    cursor: pointer;
    transition: background 0.15s;
  }}
  button:hover {{
    background: #a84e24;
  }}
  .error {{
    font-size: 13px;
    color: #b83232;
    margin-bottom: 12px;
    display: none;
  }}
  .mcp-badge {{
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    color: #365a8a;
    background: rgba(54, 90, 138, 0.08);
    border: 1px solid rgba(54, 90, 138, 0.2);
    border-radius: 3px;
    padding: 2px 6px;
    margin-bottom: 16px;
  }}
</style>
</head>
<body>
<div class="container">
  <h1>ログイン</h1>
  <p class="subtitle">Millicall PBXアカウントで認証してください</p>
  <div class="card">
    <div class="mcp-badge">MCP接続</div>
    <div class="error" id="error"></div>
    <form method="post" action="/mcp-login/callback">
      <input type="hidden" name="client_id" value="{client_id}">
      <input type="hidden" name="redirect_uri" value="{redirect_uri}">
      <input type="hidden" name="code_challenge" value="{code_challenge}">
      <input type="hidden" name="state" value="{state}">
      <input type="hidden" name="scopes" value="{scopes}">
      <div class="form-group">
        <label for="username">ユーザー名</label>
        <input type="text" id="username" name="username" required autofocus>
      </div>
      <div class="form-group">
        <label for="password">パスワード</label>
        <input type="password" id="password" name="password" required>
      </div>
      <button type="submit">認証</button>
    </form>
  </div>
</div>
</body>
</html>"""


@app.post("/mcp-login/callback")
async def mcp_login_callback(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    state: str = Form(""),
    scopes: str = Form(""),
    username: str = Form(...),
    password: str = Form(...),
):
    """Authenticate user and redirect back to MCP client with auth code."""
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.user_repo import UserRepository
    from millicall.presentation.auth import verify_password

    # Authenticate
    async with async_session() as session:
        repo = UserRepository(session)
        user = await repo.get_by_username(username)

    if not user or not verify_password(password, user.hashed_password):
        return HTMLResponse(
            '<html><body><script>alert("ユーザー名またはパスワードが正しくありません");history.back();</script></body></html>',
            status_code=401,
        )

    # Check role allows MCP access
    role = getattr(user, "role", "admin")
    if role not in ("admin", "user", "mcp"):
        return HTMLResponse(
            '<html><body><script>alert("MCP接続の権限がありません");history.back();</script></body></html>',
            status_code=403,
        )

    # Create authorization code
    from millicall.mcp_server import oauth_provider

    scope_list = [s for s in scopes.split(",") if s] if scopes else []
    code = oauth_provider.create_auth_code(
        client_id=client_id,
        username=username,
        code_challenge=code_challenge,
        redirect_uri=redirect_uri,
        scopes=scope_list,
    )

    # Redirect back to MCP client
    params = {"code": code}
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(
        url=f"{redirect_uri}{separator}{urllib.parse.urlencode(params)}",
        status_code=302,
    )


# Mount MCP server (Streamable HTTP at /mcp)
try:
    from millicall.mcp_server import get_streamable_http_app

    mcp_app = get_streamable_http_app()
    # Extract session manager for lifespan initialization
    # With OAuth, session_manager is nested: route.app (RequireAuthMiddleware) -> .app (StreamableHTTPASGIApp)
    for route in mcp_app.routes:
        handler = getattr(route, "app", None)
        if hasattr(handler, "session_manager"):
            app.state.mcp_session_manager = handler.session_manager
            break
        inner = getattr(handler, "app", None)
        if inner and hasattr(inner, "session_manager"):
            app.state.mcp_session_manager = inner.session_manager
            break
    app.mount("/", mcp_app)
    logger.info("MCP server mounted at /mcp")
except Exception as e:
    logger.warning("Failed to mount MCP server: %s", e)

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
@app.exception_handler(DuplicateWorkflowNumberError)
async def conflict_handler(request: Request, exc: MillicallError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
