from fastapi import APIRouter
from app.api.v1 import resumes

api_router = APIRouter()
api_router.include_router(
    resumes.router,
    prefix="/resumes",
    tags=["resumes"]
)