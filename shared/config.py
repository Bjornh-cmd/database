from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.network import get_local_ip

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TENANTS_DIR = DATA_DIR / "tenants"
META_DB_PATH = DATA_DIR / "meta.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    admin_username: str = "admin"
    admin_password: str = "changeme"
    jwt_secret: str = "change-this-to-a-random-secret-key"
    jwt_expire_hours: int = 24
    admin_port: int = 5505
    api_port: int = 4392  # legacy, niet meer gebruikt — alles draait op admin_port
    cors_origins: str = "*"
    public_host: str = ""

    @property
    def host(self) -> str:
        if self.public_host.strip():
            return self.public_host.strip()
        return get_local_ip()

    @property
    def server_port(self) -> int:
        return self.admin_port

    @property
    def admin_base_url(self) -> str:
        return f"http://{self.host}:{self.admin_port}"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
