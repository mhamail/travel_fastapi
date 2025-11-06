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
    user_read = UserRead.model_validate(db_user)
    return api_response(200, "User Found", user_read)


@router.put("/update", response_model=UserRead)
def update_user(
    user: requireSignin,
    request: UserUpdate,
    session: GetSession,
):
    user_id = user.get("id")
    db_user = session.get(User, user_id)  # Like findById
    raiseExceptions((db_user, 404, "User not found"))
    updated_user = updateOp(db_user, request, session)
    # ✅ Handle password hash only if password provided
    if request.password:
        updated_user.password = hash_password(request.password)

    if request.phone:
        updated_user.verified = False

    session.commit()
    session.refresh(db_user)
    return api_response(200, "User Found", UserRead.model_validate(db_user))


# ✅ READ ALL
@router.get("/list", response_model=list[UserRead])  # no response_model
def list_users(
    user: requireAdmin,
    session: GetSession,
    dateRange: Optional[
        str
    ] = None,  # JSON string like '["created_at", "01-01-2025", "01-12-2025"]'
    numberRange: Optional[str] = None,  # JSON string like '["amount", "0", "100000"]'
    searchTerm: str = None,
    columnFilters: Optional[str] = Query(
        None
    ),  # e.g. '[["name","car"],["description","product"]]'
    page: int = None,
    skip: int = 0,
    limit: int = Query(10, ge=1, le=200),
):

    filters = {
        "searchTerm": searchTerm,
        "columnFilters": columnFilters,
        "dateRange": dateRange,
        "numberRange": numberRange,
        # "customFilters": customFilters,
    }

    searchFields = ["name", "phone", "email", "roles.name"]
    result = listop(
        session=session,
        Model=User,
        searchFields=searchFields,
        filters=filters,
        skip=skip,
        page=page,
        limit=limit,
    )
    if not result["data"]:
        return api_response(404, "No User found")
    data = [UserRead.model_validate(prod) for prod in result["data"]]

    return api_response(
        200,
        "User found",
        data,
        result["total"],
    )
