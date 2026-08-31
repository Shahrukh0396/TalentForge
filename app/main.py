from urllib.request import Request
from fastapi import Response
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

app = FastAPI(
    title="TalentForge Resume Processing API",
    version="1.0.0",
    description="Upload, process, and download formatted resumes.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.openapi_version = "3.0.3"



class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "*")
        print(origin)
        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Authorization, Content-Type, Ocp-Apim-Subscription-Key, Accept",
                    "Access-Control-Max-Age": "300",
                },
            )
        
        # Handle actual request
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

app.add_middleware(DynamicCORSMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["docs"])
async def root():
    return {
        "service": "TalentForge Resume Processing API",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}