from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, EmailStr, constr, field_validator, model_validator

from sqlmodel import JSON, Column, Field, Index, Relationship, SQLModel, text
from src.api.models.mediaModel import MediaRead
from src.api.core.response import api_response
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from src.api.models.roleModel import RoleRead

if TYPE_CHECKING:
    from src.api.models import Role, Ride


class UserStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class UserPhone(SQLModel):
    # User enters this during registration
    unverified_phone: Optional[str] = Field(
        default=None, description="Temporary phone until verified"
    )

    # Saved only when fully verified
    phone: Optional[str] = Field(
        default=None, index=True, description="Verified unique phone"
    )

    verified: bool = Field(default=False)


class User(
    TimeStampedModel,
    UserPhone,
    table=True,
):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    email: EmailStr = Field(max_length=191, index=True)

    email_verified: bool = Field(default=False, description="Email verification status")

    full_name: str = Field(index=True, description="Full name of the user")
    cnic: Optional[str] = Field(default=None, description="CNIC number")
    address: Optional[str] = Field(default=None, description="Address of the user")
    image: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="Image of the user"
    )
    status: UserStatus = Field(default=UserStatus.active, description="User status")
    is_root: bool = Field(default=False)
    is_active: bool = Field(default=True)
    role_id: Optional[int] = Field(default=None, foreign_key="roles.id")
    password: str = Field(nullable=False, description="Hashed password")
    country: str = Field(description="Country name (e.g., Pakistan)")
    country_code: str = Field(description="Country code (e.g., PK)")
    currency_code: str = Field(description="Currency code (e.g., PKR)")
    currency_symbol: str = Field(description="Currency symbol (e.g., ₨)")
    otp_code: Optional[str] = None
    otp_expires_at: Optional[datetime] = None
    # relation
    role: Optional["Role"] = Relationship(back_populates="users")
    rides: Optional[List["Ride"]] = Relationship(back_populates="user")

    __table_args__ = (
        # Conditional unique index for verified phones
        Index(
            "uq_users_phone_verified",
            "phone",
            unique=True,
            postgresql_where=text("verified = true"),
        ),
        # ✅ Unique verified email only
        Index(
            "uq_users_verified_email",
            "email",
            unique=True,
            postgresql_where=text("email_verified = true"),
        ),
    )


# ==============================================================
# Schemas (Pydantic style)
# ==============================================================


class UserCreate(SQLModel):
    phone: Optional[str] = None
    email: EmailStr
    password: str
    confirm_password: str
    full_name: str
    cnic: Optional[str] = None
    address: Optional[str] = None
    # file: UploadFile = File(...)
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
    phone: Optional[str] = None
    unverified_phone: Optional[str] = None
    full_name: str
    cnic: Optional[str] = None
    email: Optional[EmailStr] = None
    email_verified: bool
    address: Optional[str] = None
    image: Optional[MediaRead] = None
    status: str
    verified: bool
    country: str
    country_code: str
    currency_code: str
    currency_symbol: str


class UserRead(SQLModel, UserReadBase):
    role: Optional[UserRole] = None


class updateEmail(BaseModel):
    email: str
    password: str
    updateEmail: EmailStr


class LoginRequest(BaseModel):
    identifier: str  # phone OR email
    password: str


class UserUpdateForm:
    def __init__(
        self,
        email: Optional[str] = Form(None),
        phone: Optional[str] = Form(None),
        full_name: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
        cnic: Optional[str] = Form(None),
        password: Optional[str] = Form(None),
        confirm_password: Optional[str] = Form(None),
        country: Optional[str] = Form(None),
        country_code: Optional[str] = Form(None),
        currency_code: Optional[str] = Form(None),
        currency_symbol: Optional[str] = Form(None),
        # file upload
        file: Optional[Union[UploadFile, str]] = File(None),
    ):
        # Convert empty → None
        def clean(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip() == "":
                return None
            return v

        self.email = clean(email)
        self.phone = clean(phone)
        self.full_name = clean(full_name)
        self.address = clean(address)
        self.cnic = clean(cnic)
        self.password = clean(password)
        self.confirm_password = clean(confirm_password)
        self.country = clean(country)
        self.country_code = clean(country_code)
        self.currency_code = clean(currency_code)
        self.currency_symbol = clean(currency_symbol)
        self.file: Optional[Union[UploadFile, str]] = file


class UserUpdate(SQLModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    address: Optional[str] = None
    photo_url: Optional[str] = None
    cnic: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    country: Optional[str] = str
    country_code: Optional[str] = str
    currency_code: Optional[str] = str
    currency_symbol: Optional[str] = str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        password = values.get("password")
        confirm_password = values.get("confirm_password")

        # ✅ Only check if password provided
        if password and password != confirm_password:
            raise ValueError("Passwords do not match")

        return values


class UpdateUserByAdmin(UserUpdate):
    role_id: Optional[int] = None
    unverified_phone: Optional[str] = None
    verified: Optional[bool] = None
    email_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordWithOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str

    @model_validator(mode="before")
    def check_password_match(cls, values):
        password = values.get("new_password")
        confirm_password = values.get("confirm_password")

        # ✅ Only check if password provided
        if password and password != confirm_password:
            raise ValueError("Passwords do not match")

        return values
