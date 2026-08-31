import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "TalentForge Resume Processing API")
    app_version: str = os.getenv("APP_VERSION", "1.1.0")
    api_version: str = os.getenv("API_VERSION", "v1")


settings = Settings()
