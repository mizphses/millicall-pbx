"""Google API authentication — supports API Key and Vertex AI (service account).

Usage:
    auth = await get_google_auth(session)
    url, headers = auth.gemini_url(model="gemini-2.5-flash", action="generateContent")
    url, headers = auth.tts_url()
"""

import json
import logging
import time
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Cache for Vertex AI access tokens (they last ~1 hour)
_vertex_token_cache: dict[str, tuple[str, float]] = {}


@dataclass
class GoogleAuth:
    """Encapsulates Google API authentication for both API Key and Vertex AI modes."""

    mode: str  # "api_key" or "vertex_ai"
    api_key: str = ""
    vertex_project: str = ""
    vertex_location: str = "us-central1"
    _service_account_json: str = ""

    def gemini_url(
        self,
        model: str = "gemini-2.5-flash",
        action: str = "generateContent",
    ) -> tuple[str, dict[str, str]]:
        """Return (url, headers) for Gemini API call."""
        if self.mode == "vertex_ai":
            url = (
                f"https://{self.vertex_location}-aiplatform.googleapis.com/v1"
                f"/projects/{self.vertex_project}"
                f"/locations/{self.vertex_location}"
                f"/publishers/google/models/{model}:{action}"
            )
            token = self._get_vertex_token()
            return url, {"Authorization": f"Bearer {token}"}

        # API Key mode
        url = (
            f"https://generativelanguage.googleapis.com/v1beta"
            f"/models/{model}:{action}?key={self.api_key}"
        )
        return url, {}

    def tts_url(self) -> tuple[str, dict[str, str]]:
        """Return (url, headers) for Google Cloud TTS API call."""
        if self.mode == "vertex_ai":
            token = self._get_vertex_token()
            return (
                "https://texttospeech.googleapis.com/v1/text:synthesize",
                {"Authorization": f"Bearer {token}"},
            )

        return (
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}",
            {},
        )

    def _get_vertex_token(self) -> str:
        """Get or refresh Vertex AI access token from service account."""
        cache_key = self.vertex_project
        cached = _vertex_token_cache.get(cache_key)
        if cached:
            token, expires_at = cached
            if time.time() < expires_at - 60:  # refresh 1 min before expiry
                return token

        token = self._refresh_vertex_token()
        # Tokens last 3600 seconds
        _vertex_token_cache[cache_key] = (token, time.time() + 3600)
        return token

    def _refresh_vertex_token(self) -> str:
        """Obtain access token from service account JSON."""
        try:
            from google.auth.transport.requests import Request  # type: ignore[unresolved-import]
            from google.oauth2 import service_account  # type: ignore[unresolved-import]

            info = json.loads(self._service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            credentials.refresh(Request())
            return credentials.token
        except ImportError as exc:
            raise RuntimeError(
                "google-auth package is required for Vertex AI. "
                "Install with: pip install google-auth"
            ) from exc


async def get_google_auth(session: AsyncSession) -> GoogleAuth:
    """Build GoogleAuth from database settings."""
    from millicall.infrastructure.repositories.settings_repo import SettingsRepository

    repo = SettingsRepository(session)
    mode = await repo.get("google_auth_mode") or "api_key"

    if mode == "vertex_ai":
        return GoogleAuth(
            mode="vertex_ai",
            vertex_project=await repo.get("google_vertex_project"),
            vertex_location=await repo.get("google_vertex_location") or "us-central1",
            _service_account_json=await repo.get("google_service_account_json"),
        )

    return GoogleAuth(
        mode="api_key",
        api_key=await repo.get("google_api_key"),
    )
