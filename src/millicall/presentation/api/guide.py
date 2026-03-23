"""Dynamic guide API that reflects current system configuration."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.database import get_session
from millicall.infrastructure.repositories.extension_repo import ExtensionRepository
from millicall.infrastructure.repositories.trunk_repo import TrunkRepository
from millicall.presentation.auth import get_current_user

router = APIRouter(
    prefix="/api/guide",
    tags=["guide"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/outbound")
async def outbound_guide(session: AsyncSession = Depends(get_session)):
    """外線発信ガイド — トランク・プレフィックス設定を反映して動的生成."""
    trunk_repo = TrunkRepository(session)
    trunks = await trunk_repo.get_all_enabled()

    trunk_info = []
    for t in trunks:
        rules = []
        if t.outbound_prefixes:
            for entry in t.outbound_prefixes.split(","):
                entry = entry.strip()
                if not entry:
                    continue
                if ":" in entry:
                    pfx, prepend = entry.split(":", 1)
                    rules.append(
                        {
                            "prefix": pfx.strip(),
                            "prepend": prepend.strip(),
                            "example": f"{pfx.strip()}0312345678 → {prepend.strip()}0312345678",
                        }
                    )
                else:
                    rules.append(
                        {
                            "prefix": entry,
                            "prepend": "",
                            "example": f"{entry}0312345678 → 0312345678",
                        }
                    )
        trunk_info.append(
            {
                "name": t.name,
                "display_name": t.display_name,
                "did_number": t.did_number,
                "caller_id": t.caller_id,
                "host": t.host,
                "prefix_rules": rules,
                "has_prefix": bool(rules),
            }
        )

    return {
        "trunks": trunk_info,
        "dialing_rules": {
            "internal": "内線番号をそのままダイヤル（例: 4001）",
            "external_default": "0 + 電話番号（プレフィックスなしのトランク）",
            "external_184": "184 + 0 + 電話番号（非通知発信）",
            "external_186": "186 + 0 + 電話番号（番号通知発信）",
            "echo_test": "*43（エコーテスト）",
        },
    }


@router.get("/mcp-config")
async def mcp_config(session: AsyncSession = Depends(get_session)):
    """MCP設定ガイド — 現在のシステム構成を反映."""
    ext_repo = ExtensionRepository(session)
    trunk_repo = TrunkRepository(session)
    extensions = await ext_repo.get_all()
    trunks = await trunk_repo.get_all_enabled()

    return {
        "remote_config": {
            "mcpServers": {
                "millicall": {
                    "type": "url",
                    "url": "https://<your-domain>/mcp",
                }
            }
        },
        "stdio_config": {
            "mcpServers": {
                "millicall": {
                    "command": "docker",
                    "args": [
                        "exec",
                        "-i",
                        "millicall-pbx",
                        "python",
                        "-m",
                        "millicall.mcp_server",
                    ],
                }
            }
        },
        "available_tools": [
            {"name": "dial", "description": "電話を発信する", "category": "通話制御"},
            {"name": "say", "description": "TTSでテキストを読み上げる", "category": "通話制御"},
            {
                "name": "listen",
                "description": "相手の発話を録音→テキスト変換",
                "category": "通話制御",
            },
            {"name": "hangup", "description": "通話を終了する", "category": "通話制御"},
            {"name": "send_dtmf", "description": "DTMFトーンを送信する", "category": "通話制御"},
            {"name": "transfer", "description": "通話を転送する", "category": "通話制御"},
            {
                "name": "get_call_status",
                "description": "通話状態を確認する",
                "category": "通話制御",
            },
            {
                "name": "list_active_calls",
                "description": "アクティブな通話一覧",
                "category": "通話制御",
            },
            {"name": "list_contacts", "description": "電話帳を検索する", "category": "電話帳"},
            {"name": "add_contact", "description": "連絡先を追加する", "category": "電話帳"},
            {"name": "delete_contact", "description": "連絡先を削除する", "category": "電話帳"},
            {"name": "list_extensions", "description": "内線番号一覧を取得", "category": "情報"},
            {"name": "list_trunks", "description": "外線トランク一覧を取得", "category": "情報"},
        ],
        "current_extensions": [
            {"number": e.number, "name": e.display_name, "type": e.type}
            for e in extensions
            if e.enabled
        ],
        "current_trunks": [
            {
                "name": t.name,
                "display_name": t.display_name,
                "did": t.did_number,
                "prefixes": t.outbound_prefixes,
            }
            for t in trunks
        ],
        "conversation_examples": [
            {
                "title": "テキストベース会話",
                "steps": [
                    'channel = dial("09012345678")',
                    'say(channel, "お忙しいところ失礼いたします")',
                    "response = listen(channel)",
                    'say(channel, "ありがとうございます")',
                    "hangup(channel)",
                ],
            },
            {
                "title": "電話帳から発信",
                "steps": [
                    'contacts = list_contacts("田中")',
                    "channel = dial(contacts[0].phone_number)",
                    'say(channel, "田中様、明日の会議の件でご連絡しました")',
                    "listen(channel)",
                    "hangup(channel)",
                ],
            },
        ],
    }
