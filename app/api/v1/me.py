from fastapi import APIRouter, Depends

from app.auth import current_user

router = APIRouter()


@router.get("/me")
def read_me(user: dict = Depends(current_user)):
    return user
