"""Settings service - reads API keys and configuration from DB."""

import os

from sqlalchemy.ext.asyncio import AsyncSession

from millicall.infrastructure.repositories.settings_repo import SettingsRepository


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.repo = SettingsRepository(session)

    async def get_all(self) -> list[dict]:
        return await self.repo.get_all_with_desc()

    async def get(self, key: str) -> str:
        """Get setting value from DB. Falls back to env var for initial setup."""
        value = await self.repo.get(key)
        if value:
            return value
        # Env var fallback (for initial bootstrap only)
        return os.environ.get(key.upper(), "")

    async def set(self, key: str, value: str) -> None:
        await self.repo.set(key, value)

    async def get_api_key(self, provider: str) -> str:
        """Get API key for a provider.

        For Google, check auth mode — if vertex_ai, the API key is not used
        (authentication is handled by GoogleAuth with service account).
        """
        key_map = {
            "google": "google_api_key",
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "coefont_key": "coefont_access_key",
            "coefont_secret": "coefont_access_secret",
        }
        setting_key = key_map.get(provider, "")
        if not setting_key:
            return ""
        return await self.get(setting_key)
