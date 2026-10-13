import os

from dotenv import load_dotenv

load_dotenv()


def _browser_origins(value: str) -> list[str]:
    """Origins the browser will actually send. A trailing slash never matches."""
    origin = value.strip().rstrip("/")
    if not origin:
        return []

    origins = [origin]
    if "://localhost" in origin:
        origins.append(origin.replace("://localhost", "://127.0.0.1", 1))
    elif "://127.0.0.1" in origin:
        origins.append(origin.replace("://127.0.0.1", "://localhost", 1))
    return origins


class Settings:
    app_name: str = os.getenv("APP_NAME", "TalentForge Resume Processing API")
    app_version: str = os.getenv("APP_VERSION", "1.1.0")
    api_version: str = os.getenv("API_VERSION", "v1")
    entra_tenant_id: str = os.getenv("ENTRA_TENANT_ID", "")
    api_client_id: str = os.getenv("API_CLIENT_ID", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "").strip().rstrip("/")
    allowed_origins: list[str] = _browser_origins(os.getenv("FRONTEND_ORIGIN", ""))


settings = Settings()
