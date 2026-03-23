"""Millicall PBX MCP Server.

Provides tools for call management, contacts, and PBX administration
via the Model Context Protocol (stdio transport for Claude Desktop).
"""

import asyncio
import json
import logging
import os

import httpx

from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ARI configuration (same as ari_handler.py)
# ---------------------------------------------------------------------------
ARI_URL = os.environ.get("ARI_URL", "http://localhost:8088")
ARI_USER = os.environ.get("ARI_USER", "millicall")
ARI_PASSWORD = os.environ.get("ARI_PASSWORD", "millicall")
STASIS_APP = "millicall-mcp"

# Database URL (used for direct DB access for contacts/extensions)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/millicall.db")

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Millicall PBX",
    instructions="IP-PBX管理・電話発信・通話制御ツール",
)


# ---------------------------------------------------------------------------
# ARI helpers
# ---------------------------------------------------------------------------
async def _ari_request(
    method: str, path: str, **kwargs
) -> dict | list | bytes | None:
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
# Call Management Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def dial(
    phone_number: str, caller_id: str = "", trunk: str = ""
) -> str:
    """外線または内線に電話を発信します。

    Args:
        phone_number: 発信先の電話番号（外線は0から始まる番号、内線は内線番号）
        caller_id: 発信者番号（省略時はトランクのデフォルト）
        trunk: 使用するトランク名（省略時はデフォルトトランク）

    Returns:
        通話のchannel_id
    """
    # Determine endpoint
    if trunk:
        endpoint = f"PJSIP/{phone_number}@{trunk}"
    elif phone_number.startswith("0") or phone_number.startswith("184") or phone_number.startswith("186"):
        # External call - find a trunk
        session_factory, engine = await _get_db_session()
        try:
            async with session_factory() as session:
                from millicall.infrastructure.repositories.trunk_repo import TrunkRepository

                repo = TrunkRepository(session)
                trunks = await repo.get_all()
                enabled_trunks = [t for t in trunks if t.enabled]
                if not enabled_trunks:
                    return json.dumps({"error": "利用可能なトランクがありません"}, ensure_ascii=False)
                trunk_obj = enabled_trunks[0]
                endpoint = f"PJSIP/{phone_number}@{trunk_obj.name}"
                if not caller_id and trunk_obj.caller_id:
                    caller_id = trunk_obj.caller_id
        finally:
            await engine.dispose()
    else:
        # Internal extension
        endpoint = f"PJSIP/{phone_number}"

    # Build originate parameters
    params = {
        "endpoint": endpoint,
        "app": STASIS_APP,
        "appArgs": phone_number,
    }
    if caller_id:
        params["callerId"] = caller_id

    try:
        result = await _ari_request("POST", "/channels", params=params)
        if isinstance(result, dict):
            channel_id = result.get("id", "")
            state = result.get("state", "")
            return json.dumps(
                {
                    "channel_id": channel_id,
                    "state": state,
                    "endpoint": endpoint,
                    "message": f"{phone_number} に発信しました",
                },
                ensure_ascii=False,
            )
        return json.dumps({"error": "予期しないレスポンス"}, ensure_ascii=False)
    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"error": f"発信に失敗しました: {e.response.status_code} {e.response.text}"},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"発信エラー: {e}"}, ensure_ascii=False)


@mcp.tool()
async def say(
    channel_id: str, text: str, voice: str = "ja-JP-Chirp3-HD-Aoede"
) -> str:
    """通話中の相手にテキストを音声で伝えます（TTS）。

    Args:
        channel_id: 通話のチャネルID
        text: 読み上げるテキスト
        voice: Google TTSのボイス名

    Returns:
        再生完了メッセージ
    """
    try:
        api_key = await _get_api_key("google")
        from millicall.phase2.tts_google import synthesize

        audio_wav = await synthesize(text, api_key, voice_name=voice)

        safe_id = _sanitize_id(channel_id)
        filename = f"mcp_say_{safe_id}.wav"
        sound_name = await _save_wav_to_asterisk(audio_wav, filename)

        await _ari_request(
            "POST",
            f"/channels/{channel_id}/play",
            params={"media": f"sound:{sound_name}"},
        )

        # Wait for playback to finish (approximate from audio size)
        duration = len(audio_wav) / (8000 * 2)
        await asyncio.sleep(duration + 0.5)

        # Clean up temp file
        try:
            filepath = f"/usr/share/asterisk/sounds/en/{sound_name}.wav"
            os.remove(filepath)
        except OSError:
            pass

        return json.dumps(
            {"status": "ok", "message": f"「{text[:50]}」を再生しました", "duration_sec": round(duration, 1)},
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"TTS再生に失敗: {e}"}, ensure_ascii=False)


@mcp.tool()
async def listen(channel_id: str, max_seconds: int = 15) -> str:
    """通話中の相手の発話を録音してテキストに変換します（STT）。

    Args:
        channel_id: 通話のチャネルID
        max_seconds: 最大録音秒数

    Returns:
        相手が話した内容のテキスト
    """
    safe_id = _sanitize_id(channel_id)
    recording_name = f"mcp_listen_{safe_id}"

    try:
        # Start recording
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

        # Poll for recording completion
        audio_data = None
        for _ in range(max_seconds + 5):
            await asyncio.sleep(1)
            try:
                result = await _ari_request(
                    "GET", f"/recordings/stored/{recording_name}/file"
                )
                if result and isinstance(result, bytes) and len(result) > 100:
                    audio_data = result
                    break
            except Exception:
                continue

        if not audio_data:
            return json.dumps({"text": "", "message": "録音データが取得できませんでした"}, ensure_ascii=False)

        # STT
        from millicall.phase2.stt import transcribe

        stt_key = await _get_api_key("openai")
        text = await transcribe(audio_data, stt_key)

        # Clean up recording
        try:
            await _ari_request("DELETE", f"/recordings/stored/{recording_name}")
        except Exception:
            pass

        return json.dumps(
            {"text": text, "message": "音声をテキストに変換しました" if text else "音声が検出されませんでした"},
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
            return json.dumps({"status": "ok", "message": "通話は既に終了しています"}, ensure_ascii=False)
        return json.dumps({"error": f"通話終了に失敗: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"通話終了エラー: {e}"}, ensure_ascii=False)


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
            return json.dumps({"error": "チャネルが見つかりません（通話が終了している可能性があります）"}, ensure_ascii=False)
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
    return """# Millicall PBX 外線発信ガイド

## 基本的な発信方法
1. `list_trunks` で利用可能なトランクとプレフィックスを確認
2. `dial` ツールで発信（phone_number に電話番号を指定）
3. 通話が接続されたら `say` で話す、`listen` で聞く
4. `hangup` で通話終了

## 電話番号の形式
- 内線: 番号をそのまま（例: "4001"）
- 外線: 0 + 番号（例: "09012345678"）
- 非通知発信: 184 + 0 + 番号
- 番号通知発信: 186 + 0 + 番号
- プレフィックス付き: トランクのプレフィックス + 番号

## 会話の流れ
### テキストベース会話
```
channel = dial("09012345678")
say(channel, "こんにちは、○○の件でお電話しました")
response = listen(channel)  # 相手の返答をテキストで取得
say(channel, "承知しました。ありがとうございます")
hangup(channel)
```

## 電話帳の活用
- `list_contacts` で連絡先を検索
- `add_contact` で新しい連絡先を保存
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
