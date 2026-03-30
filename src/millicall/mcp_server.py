"""Millicall PBX MCP Server.

Provides tools for call management, contacts, and PBX administration
via the Model Context Protocol (stdio transport for Claude Desktop).
"""

import asyncio
import contextlib
import json
import logging
import os
import secrets
import time
import urllib.parse
from dataclasses import dataclass, field

import httpx
from mcp.server.auth.provider import AuthorizationParams
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl

from millicall.config import settings as _settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAuth configuration
# ---------------------------------------------------------------------------
MCP_ISSUER_URL = os.environ.get("MCP_ISSUER_URL", "https://millicall.miz.cab")


@dataclass
class StoredAuthCode:
    code: str
    client_id: str
    scopes: list[str]
    code_challenge: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    username: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default=0.0)

    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = self.created_at + 600  # 10 minutes


@dataclass
class StoredToken:
    token: str
    client_id: str
    username: str
    scopes: list[str]
    expires_at: float
    token_type: str = "access"  # "access" or "refresh"


class MillicallOAuthProvider:
    """OAuth 2.1 provider backed by Millicall user database."""

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._auth_codes: dict[str, StoredAuthCode] = {}
        self._access_tokens: dict[str, StoredToken] = {}
        self._refresh_tokens: dict[str, StoredToken] = {}

    # -- Client registration (DCR) --

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        assert client_info.client_id is not None
        self._clients[client_info.client_id] = client_info
        logger.info("MCP OAuth: registered client %s", client_info.client_id)

    # -- Authorization --

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        # Redirect to our login page with OAuth params
        login_params = {
            "client_id": client.client_id,
            "redirect_uri": str(params.redirect_uri),
            "code_challenge": params.code_challenge,
            "state": params.state or "",
            "scopes": ",".join(params.scopes) if params.scopes else "",
        }
        return f"{MCP_ISSUER_URL}/mcp-login?{urllib.parse.urlencode(login_params)}"

    # -- Auth code management --

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> StoredAuthCode | None:
        code = self._auth_codes.get(authorization_code)
        if code and code.client_id == client.client_id:
            # Expire after 10 minutes
            if time.time() - code.created_at > 600:
                del self._auth_codes[authorization_code]
                return None
            return code
        return None

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: StoredAuthCode
    ) -> OAuthToken:
        # Remove used code
        self._auth_codes.pop(authorization_code.code, None)

        # Generate tokens
        access_token = secrets.token_urlsafe(48)
        refresh_token = secrets.token_urlsafe(48)
        expires_in = 86400  # 24 hours
        assert client.client_id is not None

        self._access_tokens[access_token] = StoredToken(
            token=access_token,
            client_id=client.client_id,
            username=authorization_code.username,
            scopes=authorization_code.scopes,
            expires_at=time.time() + expires_in,
        )
        self._refresh_tokens[refresh_token] = StoredToken(
            token=refresh_token,
            client_id=client.client_id,
            username=authorization_code.username,
            scopes=authorization_code.scopes,
            expires_at=time.time() + 86400 * 30,  # 30 days
            token_type="refresh",
        )

        logger.info("MCP OAuth: issued tokens for user %s", authorization_code.username)
        return OAuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
        )

    # -- Refresh token --

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> StoredToken | None:
        token = self._refresh_tokens.get(refresh_token)
        if token and token.client_id == client.client_id:
            if time.time() > token.expires_at:
                del self._refresh_tokens[refresh_token]
                return None
            return token
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: StoredToken,
        scopes: list[str],
    ) -> OAuthToken:
        # Revoke old refresh token
        self._refresh_tokens.pop(refresh_token.token, None)

        # Issue new tokens
        new_access = secrets.token_urlsafe(48)
        new_refresh = secrets.token_urlsafe(48)
        expires_in = 86400
        use_scopes = scopes or refresh_token.scopes
        assert client.client_id is not None

        self._access_tokens[new_access] = StoredToken(
            token=new_access,
            client_id=client.client_id,
            username=refresh_token.username,
            scopes=use_scopes,
            expires_at=time.time() + expires_in,
        )
        self._refresh_tokens[new_refresh] = StoredToken(
            token=new_refresh,
            client_id=client.client_id,
            username=refresh_token.username,
            scopes=use_scopes,
            expires_at=time.time() + 86400 * 30,
            token_type="refresh",
        )

        return OAuthToken(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=expires_in,
            scope=" ".join(use_scopes) if use_scopes else None,
        )

    # -- Access token verification --

    async def load_access_token(self, token: str) -> StoredToken | None:
        stored = self._access_tokens.get(token)
        if stored and time.time() < stored.expires_at:
            return stored
        if stored:
            del self._access_tokens[token]
        return None

    # -- Revocation --

    async def revoke_token(self, token: StoredToken) -> None:
        self._access_tokens.pop(token.token, None)
        self._refresh_tokens.pop(token.token, None)

    # -- Helper: create auth code after user login --

    def create_auth_code(
        self,
        client_id: str,
        username: str,
        code_challenge: str,
        redirect_uri: str,
        scopes: list[str],
        redirect_uri_provided_explicitly: bool = True,
    ) -> str:
        code = secrets.token_urlsafe(32)
        self._auth_codes[code] = StoredAuthCode(
            code=code,
            client_id=client_id,
            scopes=scopes,
            code_challenge=code_challenge,
            redirect_uri=redirect_uri,
            redirect_uri_provided_explicitly=redirect_uri_provided_explicitly,
            username=username,
        )
        return code


# Singleton — shared between MCP server and login endpoint
oauth_provider = MillicallOAuthProvider()


# ---------------------------------------------------------------------------
# ARI configuration (same as ari_handler.py)
# ---------------------------------------------------------------------------
ARI_URL = os.environ.get("ARI_URL", "http://localhost:8088")
ARI_USER = _settings.ari_user
ARI_PASSWORD = _settings.ari_password
STASIS_APP = "millicall-mcp"

# Database URL (used for direct DB access for contacts/extensions)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/millicall.db")

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Millicall PBX",
    instructions="""\
Millicall PBX — IP電話の発信・通話制御ツール。

## 電話をかける時
常に `converse` ツールを最優先で使ってください。
converseは発信→自律会話→切電まで全自動で行います。
あなたは目的(purpose)と要点(key_points)を渡すだけです。

dial, say, say_and_listen, listen, hangup はユーザーが明示的に手動制御を指示した場合のみ使用してください。
デフォルトでは常にconverseを選んでください。

## converseの使い方
- purpose: 会話の目的を具体的に書く（例: "ラーメンを1杯注文する"）
- key_points: 伝えるべき情報を改行区切りで書く（例: "味噌ラーメン\\n大盛り"）
- your_name: 名乗る名前（任意）

## その他のツール
- `list_contacts` / `add_contact` / `delete_contact`: 電話帳
- `list_extensions` / `list_trunks`: PBX情報

## 禁止事項
- ユーザーの明示的な指示なしに電話をかけないでください。
- ユーザーに確認せず勝手にかけ直さないでください。
""",
    transport_security=TransportSecuritySettings(
        allowed_hosts=["millicall.miz.cab", "localhost", "127.0.0.1", "192.168.1.2"],
    ),
    auth_server_provider=oauth_provider,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(MCP_ISSUER_URL),
        resource_server_url=AnyHttpUrl(MCP_ISSUER_URL),
        client_registration_options=ClientRegistrationOptions(enabled=True),
    ),
)


# ---------------------------------------------------------------------------
# ARI helpers
# ---------------------------------------------------------------------------
async def _ari_request(method: str, path: str, **kwargs) -> dict | list | bytes | None:
    """Make an ARI REST API request."""
    url = f"{ARI_URL}/ari{path}"
    params = kwargs.pop("params", {})
    params["api_key"] = f"{ARI_USER}:{ARI_PASSWORD}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, params=params, **kwargs)
        if response.status_code == 204:
            return None
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content


def _sanitize_id(channel_id: str) -> str:
    """Remove dots from channel IDs for safe filenames."""
    return channel_id.replace(".", "_")


async def _save_wav_to_asterisk(audio_wav: bytes, filename: str) -> str:
    """Save WAV audio to a file Asterisk can play and return the sound name."""
    sounds_path = f"/usr/share/asterisk/sounds/en/millicall/{filename}"
    os.makedirs(os.path.dirname(sounds_path), exist_ok=True)
    with open(sounds_path, "wb") as f:
        f.write(audio_wav)
    return f"millicall/{filename.rsplit('.', 1)[0]}"


# ---------------------------------------------------------------------------
# Database session helper
# ---------------------------------------------------------------------------
async def _get_db_session():
    """Create an async database session."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return session_factory, engine


async def _get_api_key(provider: str) -> str:
    """Get API key from DB settings (with env fallback)."""
    session_factory, engine = await _get_db_session()
    try:
        async with session_factory() as session:
            from millicall.application.settings_service import SettingsService

            svc = SettingsService(session)
            key = await svc.get_api_key(provider)
        if not key:
            raise RuntimeError(f"API key not configured for: {provider}")
        return key
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# LLM helper for autonomous conversation
# ---------------------------------------------------------------------------
async def _llm_respond(
    system_prompt: str, conversation_history: list[dict], model: str = "gpt-4o-mini"
) -> str:
    """Generate a response using OpenAI API."""
    api_key = await _get_api_key("openai")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}] + conversation_history,
                "max_tokens": 200,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Call Management Tools
# ---------------------------------------------------------------------------
async def _resolve_endpoint(
    phone_number: str, trunk: str = "", caller_id: str = ""
) -> tuple[str, str]:
    """Resolve phone_number to a PJSIP endpoint and caller_id."""
    if trunk:
        return f"PJSIP/{phone_number}@{trunk}", caller_id
    elif (
        phone_number.startswith("0")
        or phone_number.startswith("184")
        or phone_number.startswith("186")
    ):
        session_factory, engine = await _get_db_session()
        try:
            async with session_factory() as session:
                from millicall.infrastructure.repositories.trunk_repo import TrunkRepository

                repo = TrunkRepository(session)
                trunks = await repo.get_all()
                enabled_trunks = [t for t in trunks if t.enabled]
                if not enabled_trunks:
                    raise ValueError("利用可能なトランクがありません")
                trunk_obj = enabled_trunks[0]
                if not caller_id and trunk_obj.caller_id:
                    caller_id = trunk_obj.caller_id
                return f"PJSIP/{phone_number}@{trunk_obj.name}", caller_id
        finally:
            await engine.dispose()
    else:
        session_factory, engine = await _get_db_session()
        try:
            async with session_factory() as session:
                from sqlalchemy import text as sa_text

                row = await session.execute(
                    sa_text(
                        "SELECT p.username FROM extensions e "
                        "JOIN peers p ON p.id = e.peer_id "
                        "WHERE e.number = :num AND e.enabled = 1"
                    ),
                    {"num": phone_number},
                )
                result = row.fetchone()
                ep = f"PJSIP/{result[0]}" if result else f"PJSIP/{phone_number}"
                return ep, caller_id
        finally:
            await engine.dispose()


async def _tts_play(channel_id: str, text: str, voice: str = "ja-JP-Chirp3-HD-Aoede") -> float:
    """Synthesize text and play on channel. Returns duration in seconds."""
    api_key = await _get_api_key("google")
    from millicall.phase2.ari_handler import _get_google_auth
    from millicall.phase2.tts_google import synthesize

    auth = await _get_google_auth()
    audio_wav = await synthesize(text, api_key, voice_name=voice, google_auth=auth)

    safe_id = _sanitize_id(channel_id)
    filename = f"mcp_say_{safe_id}.wav"
    sound_name = await _save_wav_to_asterisk(audio_wav, filename)

    await _ari_request(
        "POST",
        f"/channels/{channel_id}/play",
        params={"media": f"sound:{sound_name}"},
    )

    duration = len(audio_wav) / (8000 * 2)
    await asyncio.sleep(duration + 0.5)

    with contextlib.suppress(OSError):
        os.remove(f"/usr/share/asterisk/sounds/en/{sound_name}.wav")
    return duration


async def _record_and_transcribe(channel_id: str, max_seconds: int = 15) -> str:
    """Record from channel and return transcribed text."""
    safe_id = _sanitize_id(channel_id)
    recording_name = f"mcp_listen_{safe_id}"

    await _ari_request(
        "POST",
        f"/channels/{channel_id}/record",
        params={
            "name": recording_name,
            "format": "wav",
            "maxDurationSeconds": max_seconds,
            "maxSilenceSeconds": 3,
            "beep": "false",
            "terminateOn": "none",
        },
    )

    audio_data = None
    for _ in range(max_seconds + 5):
        await asyncio.sleep(1)
        try:
            result = await _ari_request("GET", f"/recordings/stored/{recording_name}/file")
            if result and isinstance(result, bytes) and len(result) > 100:
                audio_data = result
                break
        except Exception:
            continue

    if not audio_data:
        return ""

    from millicall.phase2.stt import transcribe

    stt_key = await _get_api_key("openai")
    text = await transcribe(audio_data, stt_key)

    with contextlib.suppress(Exception):
        await _ari_request("DELETE", f"/recordings/stored/{recording_name}")
    return text


@mcp.tool()
async def dial(phone_number: str, caller_id: str = "", trunk: str = "") -> str:
    """電話を発信し、相手が応答するまで待ちます。応答したらchannel_idを返します。

    Args:
        phone_number: 発信先（外線は0始まりの番号、内線は内線番号 例: "800"）
        caller_id: 発信者番号（省略時はトランクのデフォルト）
        trunk: 使用するトランク名（省略時は自動選択）

    Returns:
        channel_idと接続状態。このchannel_idをsay_and_listen等に渡してください。
    """
    try:
        endpoint, caller_id = await _resolve_endpoint(phone_number, trunk, caller_id)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    params = {
        "endpoint": endpoint,
        "app": STASIS_APP,
        "appArgs": phone_number,
    }
    if caller_id:
        params["callerId"] = caller_id

    try:
        result = await _ari_request("POST", "/channels", params=params)
        if not isinstance(result, dict):
            return json.dumps({"error": "予期しないレスポンス"}, ensure_ascii=False)

        channel_id = result.get("id", "")

        # Wait for answer (poll up to 30 seconds)
        for _ in range(30):
            await asyncio.sleep(1)
            try:
                status = await _ari_request("GET", f"/channels/{channel_id}")
                if isinstance(status, dict) and status.get("state") == "Up":
                    return json.dumps(
                        {
                            "channel_id": channel_id,
                            "state": "Up",
                            "message": f"{phone_number} が応答しました。say_and_listenで会話を始めてください。",
                        },
                        ensure_ascii=False,
                    )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return json.dumps(
                        {"error": "相手が応答しませんでした（不在または拒否）"},
                        ensure_ascii=False,
                    )

        return json.dumps(
            {"error": "30秒以内に応答がありませんでした", "channel_id": channel_id},
            ensure_ascii=False,
        )
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"発信に失敗しました: {e.response.status_code} {e.response.text}"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"発信エラー: {e}"}, ensure_ascii=False)


@mcp.tool()
async def say_and_listen(
    channel_id: str,
    text: str,
    max_listen_seconds: int = 15,
    voice: str = "ja-JP-Chirp3-HD-Aoede",
) -> str:
    """相手にテキストを話しかけ、その後相手の返答を聞き取ります。
    会話の1ターン（こちらが話す→相手が話す）を1回のツール呼び出しで行います。

    Args:
        channel_id: 通話のチャネルID（dialの戻り値）
        text: 相手に伝えるテキスト
        max_listen_seconds: 相手の発話を待つ最大秒数
        voice: Google TTSのボイス名

    Returns:
        相手の返答テキスト
    """
    try:
        # Step 1: Speak
        await _tts_play(channel_id, text, voice)

        # Step 2: Listen for response
        response_text = await _record_and_transcribe(channel_id, max_listen_seconds)

        return json.dumps(
            {
                "you_said": text[:100],
                "they_said": response_text,
                "message": response_text
                if response_text
                else "（相手の発話が検出されませんでした）",
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"会話エラー: {e}"}, ensure_ascii=False)


@mcp.tool()
async def say(channel_id: str, text: str, voice: str = "ja-JP-Chirp3-HD-Aoede") -> str:
    """相手にテキストを話します（返答は聞きません）。
    通話の最後の挨拶やお礼など、返答を待たない場面で使います。

    Args:
        channel_id: 通話のチャネルID
        text: 読み上げるテキスト
        voice: Google TTSのボイス名

    Returns:
        再生完了メッセージ
    """
    try:
        duration = await _tts_play(channel_id, text, voice)
        return json.dumps(
            {
                "status": "ok",
                "message": f"「{text[:50]}」を再生しました",
                "duration_sec": round(duration, 1),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"TTS再生に失敗: {e}"}, ensure_ascii=False)


@mcp.tool()
async def listen(channel_id: str, max_seconds: int = 15) -> str:
    """相手の発話だけを聞き取ります（こちらは何も話しません）。
    相手がまだ話し続けている場合など、追加で聞きたい時に使います。

    Args:
        channel_id: 通話のチャネルID
        max_seconds: 最大録音秒数

    Returns:
        相手が話した内容のテキスト
    """
    try:
        text = await _record_and_transcribe(channel_id, max_seconds)
        return json.dumps(
            {"text": text, "message": text if text else "（相手の発話が検出されませんでした）"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"録音/STTに失敗: {e}"}, ensure_ascii=False)


@mcp.tool()
async def hangup(channel_id: str) -> str:
    """通話を終了します。

    Args:
        channel_id: 通話のチャネルID

    Returns:
        終了結果メッセージ
    """
    try:
        await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "16"})
        return json.dumps({"status": "ok", "message": "通話を終了しました"}, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps(
                {"status": "ok", "message": "通話は既に終了しています"}, ensure_ascii=False
            )
        return json.dumps({"error": f"通話終了に失敗: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"通話終了エラー: {e}"}, ensure_ascii=False)


@mcp.tool()
async def converse(
    phone_number: str,
    purpose: str,
    key_points: str = "",
    your_name: str = "",
    max_turns: int = 10,
    caller_id: str = "",
    trunk: str = "",
    voice: str = "ja-JP-Chirp3-HD-Aoede",
) -> str:
    """電話を発信し、目的に沿って自律的に会話を行います。
    会話の目的と要点を指定するだけで、発信→会話→切電まで自動で行います。

    Args:
        phone_number: 発信先（外線: "09012345678"、内線: "800"）
        purpose: 会話の目的（例: "ラーメンを1杯注文する"、"明日の会議の時間を確認する"）
        key_points: 伝えるべき要点（改行区切り。例: "味噌ラーメン\\n大盛り\\n届け先は東京都..."）
        your_name: 自分の名前（名乗る時に使用。省略時は名乗りません）
        max_turns: 最大会話ターン数（デフォルト10）
        caller_id: 発信者番号（省略時はデフォルト）
        trunk: トランク名（省略時は自動選択）
        voice: TTSボイス名

    Returns:
        会話の全文トランスクリプトと結果サマリー
    """
    # Build system prompt for the conversation agent
    name_part = f"あなたの名前は「{your_name}」です。最初に名乗ってください。" if your_name else ""
    points_part = f"\n\n## 伝えるべき要点\n{key_points}" if key_points else ""

    system_prompt = f"""\
あなたは電話で会話をしているAIアシスタントです。
相手は電話の向こうにいる人間です。自然な日本語の電話会話を行ってください。

## 会話の目的
{purpose}

{name_part}{points_part}

## 重要なルール
- 1回の発話は1〜2文に留めてください。電話では短く区切って話すのが自然です。
- 敬語を使ってください。
- 相手の発話に適切に反応してください（相槌、確認、質問への回答など）。
- 目的が達成できたら「ありがとうございました。失礼いたします。」のように締めの挨拶をして、[DONE] を発話の末尾に付けてください。
- 目的が達成できない場合（相手が断った等）も、丁寧に終了して [DONE] を付けてください。
- [DONE] は相手には読み上げられません。会話終了の合図としてだけ使います。
- 相手の発話が空だった場合は「もしもし、聞こえていますか？」と確認してください。
- わからないことを聞かれたら「確認して折り返します」と伝えてください。
"""

    transcript: list[dict] = []
    conversation_history: list[dict] = []

    # Step 1: Dial
    try:
        endpoint, caller_id = await _resolve_endpoint(phone_number, trunk, caller_id)
    except ValueError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    params = {"endpoint": endpoint, "app": STASIS_APP, "appArgs": phone_number}
    if caller_id:
        params["callerId"] = caller_id

    try:
        result = await _ari_request("POST", "/channels", params=params)
        if not isinstance(result, dict):
            return json.dumps({"error": "発信に失敗しました"}, ensure_ascii=False)
        channel_id = result.get("id", "")
    except Exception as e:
        return json.dumps({"error": f"発信エラー: {e}"}, ensure_ascii=False)

    # Wait for answer
    answered = False
    for _ in range(30):
        await asyncio.sleep(1)
        try:
            status = await _ari_request("GET", f"/channels/{channel_id}")
            if isinstance(status, dict) and status.get("state") == "Up":
                answered = True
                break
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return json.dumps(
                    {"error": "相手が応答しませんでした", "transcript": transcript},
                    ensure_ascii=False,
                )

    if not answered:
        with contextlib.suppress(Exception):
            await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "16"})
        return json.dumps(
            {"error": "30秒以内に応答がありませんでした", "transcript": transcript},
            ensure_ascii=False,
        )

    # Step 2: Conversation loop
    try:
        for turn in range(max_turns):
            # Generate what to say
            ai_response = await _llm_respond(system_prompt, conversation_history)

            # Check if conversation should end
            done = "[DONE]" in ai_response
            ai_text = ai_response.replace("[DONE]", "").strip()

            if not ai_text:
                break

            transcript.append({"turn": turn + 1, "speaker": "ai", "text": ai_text})
            conversation_history.append({"role": "assistant", "content": ai_text})

            if done:
                # Final message — say without listening
                await _tts_play(channel_id, ai_text, voice)
                break
            else:
                # Say and listen
                await _tts_play(channel_id, ai_text, voice)
                their_text = await _record_and_transcribe(channel_id, 15)

                transcript.append(
                    {"turn": turn + 1, "speaker": "human", "text": their_text or "（無言）"}
                )
                conversation_history.append(
                    {"role": "user", "content": their_text or "（相手は無言でした）"}
                )

    except Exception as e:
        transcript.append({"speaker": "system", "text": f"エラー: {e}"})

    # Step 3: Hang up
    with contextlib.suppress(Exception):
        await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "16"})

    # Generate summary
    try:
        summary = await _llm_respond(
            "以下の電話会話のトランスクリプトを読んで、結果を1〜2文で要約してください。目的が達成できたかどうかも述べてください。",
            [{"role": "user", "content": json.dumps(transcript, ensure_ascii=False)}],
        )
    except Exception:
        summary = ""

    return json.dumps(
        {
            "status": "completed",
            "phone_number": phone_number,
            "purpose": purpose,
            "turns": len([t for t in transcript if t.get("speaker") == "ai"]),
            "summary": summary,
            "transcript": transcript,
        },
        ensure_ascii=False,
    )


@mcp.tool()
async def send_dtmf(channel_id: str, digits: str) -> str:
    """DTMFトーンを送信します。

    Args:
        channel_id: 通話のチャネルID
        digits: 送信するDTMFディジット（例: "1234#"）

    Returns:
        送信結果メッセージ
    """
    try:
        await _ari_request(
            "POST",
            f"/channels/{channel_id}/dtmf",
            params={"dtmf": digits, "duration": 250, "between": 100},
        )
        return json.dumps(
            {"status": "ok", "message": f"DTMF '{digits}' を送信しました"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"DTMF送信に失敗: {e}"}, ensure_ascii=False)


@mcp.tool()
async def transfer(channel_id: str, destination: str) -> str:
    """通話を別の内線番号に転送します。

    Args:
        channel_id: 通話のチャネルID
        destination: 転送先の内線番号

    Returns:
        転送結果メッセージ
    """
    try:
        # Redirect the channel to the destination extension in the default context
        await _ari_request(
            "POST",
            f"/channels/{channel_id}/redirect",
            params={"endpoint": f"PJSIP/{destination}"},
        )
        return json.dumps(
            {"status": "ok", "message": f"内線 {destination} に転送しました"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"転送に失敗: {e}"}, ensure_ascii=False)


@mcp.tool()
async def get_call_status(channel_id: str) -> str:
    """通話の現在の状態を取得します。

    Args:
        channel_id: 通話のチャネルID

    Returns:
        通話状態の情報
    """
    try:
        result = await _ari_request("GET", f"/channels/{channel_id}")
        if isinstance(result, dict):
            return json.dumps(
                {
                    "channel_id": result.get("id"),
                    "state": result.get("state"),
                    "caller_name": result.get("caller", {}).get("name", ""),
                    "caller_number": result.get("caller", {}).get("number", ""),
                    "connected_name": result.get("connected", {}).get("name", ""),
                    "connected_number": result.get("connected", {}).get("number", ""),
                    "created_at": result.get("creationtime", ""),
                },
                ensure_ascii=False,
            )
        return json.dumps({"error": "チャネル情報を取得できませんでした"}, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return json.dumps(
                {"error": "チャネルが見つかりません（通話が終了している可能性があります）"},
                ensure_ascii=False,
            )
        return json.dumps({"error": f"ステータス取得に失敗: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"ステータス取得エラー: {e}"}, ensure_ascii=False)


@mcp.tool()
async def list_active_calls() -> str:
    """現在アクティブな通話の一覧を取得します。

    Returns:
        アクティブな通話のリスト
    """
    try:
        result = await _ari_request("GET", "/channels")
        if isinstance(result, list):
            calls = []
            for ch in result:
                calls.append(
                    {
                        "channel_id": ch.get("id"),
                        "state": ch.get("state"),
                        "caller_number": ch.get("caller", {}).get("number", ""),
                        "connected_number": ch.get("connected", {}).get("number", ""),
                        "created_at": ch.get("creationtime", ""),
                    }
                )
            return json.dumps(
                {"count": len(calls), "calls": calls},
                ensure_ascii=False,
            )
        return json.dumps({"count": 0, "calls": []}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"通話一覧の取得に失敗: {e}"}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Contacts Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def list_contacts(query: str = "") -> str:
    """電話帳を検索します。queryが空の場合は全件返します。

    Args:
        query: 検索キーワード（名前、電話番号、会社名で部分一致検索）

    Returns:
        連絡先のリスト
    """
    session_factory, engine = await _get_db_session()
    try:
        async with session_factory() as session:
            from millicall.infrastructure.repositories.contact_repo import ContactRepository

            repo = ContactRepository(session)
            if query.strip():
                contacts = await repo.search(query.strip())
            else:
                contacts = await repo.get_all()

        results = [
            {
                "id": c.id,
                "name": c.name,
                "phone_number": c.phone_number,
                "company": c.company,
                "department": c.department,
                "notes": c.notes,
            }
            for c in contacts
        ]
        return json.dumps(
            {"count": len(results), "contacts": results},
            ensure_ascii=False,
        )
    finally:
        await engine.dispose()


@mcp.tool()
async def add_contact(
    name: str,
    phone_number: str,
    company: str = "",
    department: str = "",
    notes: str = "",
) -> str:
    """電話帳に連絡先を追加します。

    Args:
        name: 名前
        phone_number: 電話番号
        company: 会社名
        department: 部署名
        notes: メモ

    Returns:
        追加された連絡先の情報
    """
    from millicall.domain.models import Contact

    session_factory, engine = await _get_db_session()
    try:
        async with session_factory() as session:
            from millicall.infrastructure.repositories.contact_repo import ContactRepository

            repo = ContactRepository(session)
            contact = await repo.create(
                Contact(
                    name=name,
                    phone_number=phone_number,
                    company=company,
                    department=department,
                    notes=notes,
                )
            )
        return json.dumps(
            {
                "status": "ok",
                "message": f"連絡先「{name}」を追加しました",
                "contact": {
                    "id": contact.id,
                    "name": contact.name,
                    "phone_number": contact.phone_number,
                    "company": contact.company,
                    "department": contact.department,
                    "notes": contact.notes,
                },
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"連絡先の追加に失敗: {e}"}, ensure_ascii=False)
    finally:
        await engine.dispose()


@mcp.tool()
async def delete_contact(contact_id: int) -> str:
    """電話帳から連絡先を削除します。

    Args:
        contact_id: 削除する連絡先のID

    Returns:
        削除結果メッセージ
    """
    session_factory, engine = await _get_db_session()
    try:
        async with session_factory() as session:
            from millicall.infrastructure.repositories.contact_repo import ContactRepository

            repo = ContactRepository(session)
            await repo.delete(contact_id)
        return json.dumps(
            {"status": "ok", "message": f"連絡先 (ID: {contact_id}) を削除しました"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"連絡先の削除に失敗: {e}"}, ensure_ascii=False)
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Extensions & Trunks Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def list_extensions() -> str:
    """内線番号の一覧を取得します。

    Returns:
        内線番号のリスト
    """
    session_factory, engine = await _get_db_session()
    try:
        async with session_factory() as session:
            from millicall.infrastructure.repositories.extension_repo import ExtensionRepository

            repo = ExtensionRepository(session)
            extensions = await repo.get_all()

        results = [
            {
                "id": e.id,
                "number": e.number,
                "display_name": e.display_name,
                "enabled": e.enabled,
                "type": e.type,
            }
            for e in extensions
        ]
        return json.dumps(
            {"count": len(results), "extensions": results},
            ensure_ascii=False,
        )
    finally:
        await engine.dispose()


@mcp.tool()
async def list_trunks() -> str:
    """外線トランクの一覧と発信プレフィックスを取得します。

    Returns:
        トランクのリスト
    """
    session_factory, engine = await _get_db_session()
    try:
        async with session_factory() as session:
            from millicall.infrastructure.repositories.trunk_repo import TrunkRepository

            repo = TrunkRepository(session)
            trunks = await repo.get_all()

        results = [
            {
                "id": t.id,
                "name": t.name,
                "display_name": t.display_name,
                "did_number": t.did_number,
                "caller_id": t.caller_id,
                "outbound_prefixes": t.outbound_prefixes,
                "enabled": t.enabled,
            }
            for t in trunks
        ]
        return json.dumps(
            {"count": len(results), "trunks": results},
            ensure_ascii=False,
        )
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Guide Resource
# ---------------------------------------------------------------------------
@mcp.resource("guide://outbound-calling")
async def outbound_calling_guide() -> str:
    """外線発信のガイド"""
    return """# Millicall PBX 電話会話ガイド

## 基本の会話フロー（3ステップ）
1. `dial` で発信（応答まで自動で待ちます）
2. `say_and_listen` で会話のやりとり（何ターンでも繰り返し可能）
3. `hangup` で通話終了

## 電話番号の形式
- 内線: 番号をそのまま（例: "800", "4001"）
- 外線: 0 + 番号（例: "09012345678"）
- 非通知発信: 184 + 0 + 番号
- 番号通知発信: 186 + 0 + 番号

## 会話例：ラーメンの注文
```
# 1. 発信（応答を待つ）
result = dial("09012345678")
channel_id = result["channel_id"]

# 2. 会話（say_and_listen = こちらが話す→相手の返答を聞く）
r1 = say_and_listen(channel_id, "こんにちは、ラーメンを1杯お願いしたいのですが")
# r1["they_said"] = "はい、味はどうしますか？"

r2 = say_and_listen(channel_id, "味噌ラーメンをお願いします")
# r2["they_said"] = "かしこまりました。20分ほどでお届けします"

# 3. 最後の挨拶（返答不要なのでsayだけ）→ 切る
say(channel_id, "ありがとうございます。お願いします")
hangup(channel_id)
```

## ツール使い分け
- `say_and_listen`: 通常の会話（話す→聞く）
- `say`: 最後の一言（お礼・挨拶など返答不要）
- `listen`: 追加で相手の話を聞きたい時
- `dial`: 発信（応答まで待つ）
- `hangup`: 切電
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def get_streamable_http_app():
    """Return a Starlette/ASGI app for Streamable HTTP transport."""
    return mcp.streamable_http_app()


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if mode == "http":
        import uvicorn

        port = int(os.environ.get("MCP_PORT", "3001"))
        app = get_streamable_http_app()
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
