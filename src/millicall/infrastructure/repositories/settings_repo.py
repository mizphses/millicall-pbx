from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.orm import settings_table


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> str:
        result = await self.session.execute(
            select(settings_table.c.value).where(settings_table.c.key == key)
        )
        row = result.first()
        return row.value if row else ""

    async def get_all(self) -> dict[str, str]:
        result = await self.session.execute(select(settings_table).order_by(settings_table.c.key))
        return {row.key: row.value for row in result}

    async def get_all_with_desc(self) -> list[dict]:
        result = await self.session.execute(select(settings_table).order_by(settings_table.c.key))
        return [
            {"key": row.key, "value": row.value, "description": row.description} for row in result
        ]

    async def set(self, key: str, value: str, description: str | None = None) -> None:
        existing = await self.get(key)
        if existing or existing == "":
            # Check if key exists
            result = await self.session.execute(
                select(settings_table).where(settings_table.c.key == key)
            )
            if result.first():
                from sqlalchemy import update

                await self.session.execute(
                    update(settings_table).where(settings_table.c.key == key).values(value=value)
                )
            else:
                await self.session.execute(
                    settings_table.insert().values(key=key, value=value, description=description)
                )
        await self.session.commit()

    async def ensure_defaults(self) -> None:
        """Create default settings entries if they don't exist."""
        defaults = [
            ("coefont_access_key", "", "CoeFont API Access Key"),
            ("coefont_access_secret", "", "CoeFont API Access Secret"),
            ("google_auth_mode", "api_key", "Google認証モード (api_key / vertex_ai)"),
            ("google_api_key", "", "Google API Key (Gemini LLM & Chirp3 TTS)"),
            ("google_vertex_project", "", "Google Cloud プロジェクトID (Vertex AI)"),
            ("google_vertex_location", "us-central1", "Vertex AI リージョン"),
            ("google_service_account_json", "", "サービスアカウントJSON (Vertex AI)"),
            ("stt_provider", "openai", "STTプロバイダー (openai / google)"),
            ("openai_api_key", "", "OpenAI API Key (Whisper STT & GPT)"),
            ("anthropic_api_key", "", "Anthropic API Key (Claude)"),
        ]
        for key, default, desc in defaults:
            result = await self.session.execute(
                select(settings_table).where(settings_table.c.key == key)
            )
            if not result.first():
                await self.session.execute(
                    settings_table.insert().values(key=key, value=default, description=desc)
                )
        await self.session.commit()
