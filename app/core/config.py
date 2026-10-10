import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = os.getenv("APP_NAME", "TalentForge Resume Processing API")
    app_version: str = os.getenv("APP_VERSION", "1.1.0")
    api_version: str = os.getenv("API_VERSION", "v1")
    entra_tenant_id: str = os.getenv("ENTRA_TENANT_ID", "")
    api_client_id: str = os.getenv("API_CLIENT_ID", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "")


settings = Settings()
