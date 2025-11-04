from fastapi import APIRouter
from sqlmodel import select
from src.api.core.security import (
    hash_password,
)
from src.api.models.roleModel import Role
from src.api.models.userModel import UserCreate, User, UserRead, LoginRequest
from src.api.core import (
    GetSession,
    api_response,
    requireSignin,
    requireAdmin,
    requirePermission,
)

router = APIRouter(tags=["Auth"])


@router.post("/init", response_model=UserRead)
def initialize_first_user(
    request: UserCreate,
    session: GetSession,
):

    # Prevent rerun if roles already exist
    existing_roles = session.exec(select(Role)).all()
    if existing_roles:
        return api_response(
            400,
            "Initialization already done",
        )

    # Create roles
    admin_role = Role(
        title="root",
        permissions=["all", "system:*"],
    )

    session.add(admin_role)
    session.flush()  # get IDs without committing

    # Create first user with admin role
    hashed_password = hash_password(request.password)
    user = User(**request.model_dump())
    user.password = hashed_password
    user.verified = True
    user.is_root = True
    user.role_id = admin_role.id
    print(user)
    session.add(user)
    session.flush()

    session.commit()
    session.refresh(user)

    user_read = UserRead.model_validate(user)
    return api_response(
        200,
        "Initialized admin user and roles",
        user_read,
    )
