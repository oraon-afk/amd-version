from fastapi import APIRouter, Depends

from backend.app.auth.auth_dependencies import get_current_user
from backend.app.db.models.user import User
from backend.app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

