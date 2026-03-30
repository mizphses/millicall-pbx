import secrets
import sys
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _generate_secret() -> str:
    """Generate a cryptographically strong random secret."""
    return secrets.token_urlsafe(48)


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/millicall.db"
    asterisk_config_dir: Path = Path("/etc/asterisk")
    asterisk_templates_dir: Path = Path("./asterisk_templates")
    pbx_bind_address: str = "0.0.0.0"
    pbx_public_address: str = ""  # IP for provisioning. Auto-detected if empty.
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # JWT Auth — no insecure defaults; must be set via environment variables
    jwt_secret: str = ""
    jwt_expiry_minutes: int = 1440
    admin_password: str = ""

    # ARI (Asterisk REST Interface)
    ari_user: str = "millicall"
    ari_password: str = ""

    # Phase 2
    coefont_access_key: str = ""
    coefont_access_secret: str = ""
    coefont_voice_id: str = "cbe4e152-40a5-4c0d-91cd-2fc27d60e6bd"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def _require_jwt_secret(cls, v: str) -> str:
        if not v:
            print(
                "WARNING: JWT_SECRET is not set. Generating a random secret for this session.\n"
                "         Set JWT_SECRET in .env for persistent sessions.",
                file=sys.stderr,
            )
            return _generate_secret()
        return v

    @field_validator("admin_password", mode="before")
    @classmethod
    def _require_admin_password(cls, v: str) -> str:
        if not v:
            generated = secrets.token_urlsafe(16)
            print(
                f"WARNING: ADMIN_PASSWORD is not set. Generated temporary password: {generated}\n"
                "         Set ADMIN_PASSWORD in .env for a stable admin password.",
                file=sys.stderr,
            )
            return generated
        return v

    @field_validator("ari_password", mode="before")
    @classmethod
    def _require_ari_password(cls, v: str) -> str:
        if not v:
            generated = secrets.token_urlsafe(16)
            print(
                "WARNING: ARI_PASSWORD is not set. Generating a random password.\n"
                "         Set ARI_PASSWORD in .env to match your ari.conf.",
                file=sys.stderr,
            )
            return generated
        return v


settings = Settings()
