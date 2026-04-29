from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Resume Processing API"
    api_version: str = "v1"

settings = Settings()