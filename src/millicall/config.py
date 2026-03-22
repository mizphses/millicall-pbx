from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/millicall.db"
    asterisk_config_dir: Path = Path("/etc/asterisk")
    asterisk_templates_dir: Path = Path("./asterisk_templates")
    pbx_bind_address: str = "172.20.0.1"
    web_host: str = "0.0.0.0"
    web_port: int = 8000

    # JWT Auth
    jwt_secret: str = "millicall-dev-secret-change-me"
    jwt_expiry_minutes: int = 1440
    admin_password: str = "admin"

    # Phase 2
    coefont_access_key: str = ""
    coefont_access_secret: str = ""
    coefont_voice_id: str = "cbe4e152-40a5-4c0d-91cd-2fc27d60e6bd"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
