from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
)
from sqlalchemy import select

from src.api.core.response import api_response, raiseExceptions
from src.api.core.operation import listop

from src.api.core.security import hash_password
from src.api.core import updateOp, requireSignin
from src.api.core.dependencies import GetSession, requirePermission, requireAdmin

from src.api.models.userModel import (
    UserCreate,
    UpdateUserByAdmin,
    User,
    UserRead,
    UserReadBase,
    UserUpdate,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/read/{id}", response_model=UserRead)
def get_user(
    id: int,
    session: GetSession,
):
    user_id = id
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 400, "User not found"))

    return api_response(200, "User Found", db_user.id)
