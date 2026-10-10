from fastapi import APIRouter, Depends

from app.api.v1 import me, resumes
from app.auth import current_user

api_router = APIRouter()
api_router.include_router(
    resumes.router,
    prefix="/resumes",
    tags=["resumes"],
    dependencies=[Depends(current_user)],
)
api_router.include_router(
    me.router,
    tags=["account"],
    dependencies=[Depends(current_user)],
)