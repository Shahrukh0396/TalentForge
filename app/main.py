from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.auth import current_user
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Upload, process, and download formatted resumes.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.openapi_version = "3.0.3"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin] if settings.frontend_origin else [],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["docs"], dependencies=[Depends(current_user)])
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "api": settings.api_version,
        "docs": "/docs",
    }


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(current_user)])
async def openapi():
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False, dependencies=[Depends(current_user)])
async def swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{settings.app_name} docs")


@app.get("/redoc", include_in_schema=False, dependencies=[Depends(current_user)])
async def redoc_ui():
    return get_redoc_html(openapi_url="/openapi.json", title=f"{settings.app_name} docs")


@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "version": settings.app_version,
        "api": settings.api_version,
    }
