from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import BaseModel, EmailStr, constr, field_validator, model_validator
from sqlmodel import Field, Index, Relationship, SQLModel
from src.api.core.response import api_response
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from src.api.models.roleModel import RoleRead

if TYPE_CHECKING:
    from src.api.models import Role


class UserStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class User(TimeStampedModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    email: Optional[EmailStr] = Field(max_length=191, unique=True, index=True)
    phone: str = Field(index=True, description="User phone number")
    verified: bool = Field(default=False, description="Whether user is verified")
    # ✅ Conditional unique constraint: phone unique only when verified=True
    __table_args__ = (
        Index(
            "uq_users_phone_verified_true",
            "phone",
            unique=True,
            postgresql_where=(f"verified = true"),
        ),
    )
    full_name: str = Field(index=True, description="Full name of the user")
    cnic: Optional[str] = Field(default=None, description="CNIC number")
    address: Optional[str] = Field(default=None, description="Address of the user")
    photo_url: Optional[str] = Field(default=None, description="Profile photo URL")
    status: UserStatus = Field(default=UserStatus.active, description="User status")
    is_root: bool = Field(default=False)
    role_id: Optional[int] = Field(default=None, foreign_key="roles.id")
    role: Optional["Role"] = Relationship(back_populates="users")
    password: str = Field(nullable=False, description="Hashed password")
    country: str = Field(description="Country name (e.g., Pakistan)")
    country_code: str = Field(description="Country code (e.g., PK)")
    currency_code: str = Field(description="Currency code (e.g., PKR)")
    currency_symbol: str = Field(description="Currency symbol (e.g., ₨)")


# ==============================================================
# Schemas (Pydantic style)
# ==============================================================


class UserCreate(SQLModel):
    phone: str
    email: Optional[EmailStr] = None
    password: str
    confirm_password: str
    full_name: str
    cnic: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    country: str
    country_code: str
    currency_code: str
    currency_symbol: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values


class UserRole(SQLModel):
    id: int
    title: str
    permissions: list[str]


class UserReadBase(TimeStampReadModel):
    id: int
    phone: str
    full_name: str
    cnic: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    status: str
    verified: bool
    country: str
    country_code: str
    currency_code: str
    currency_symbol: str


class UserRead(SQLModel, UserReadBase):
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    phone: str
    password: str


class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    status: Optional[str] = None
    verified: Optional[bool] = None
    password: Optional[str] = None
    country: str
    country_code: str
    currency_code: str
    currency_symbol: str


class UpdateUserByAdmin(UserUpdate):
    role_id: Optional[int] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        if values.get("new_password") != values.get("confirm_password"):
            raise ValueError("Passwords do not match")
        return values
