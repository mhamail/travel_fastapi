from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SAEnum
import json
from typing import TYPE_CHECKING, Annotated, Any, Dict, List, Literal, Optional, Union

from fastapi import File, Form, UploadFile
from pydantic import (
    BaseModel,
    EmailStr,
    conint,
    constr,
    field_validator,
    model_validator,
)

from sqlmodel import JSON, Column, Field, Index, Relationship, SQLModel, text
from src.api.models.userModel import UserRead
from src.api.models.rideModel import CarType
from src.api.core.response import api_response
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from src.api.models.roleModel import RoleRead

car_type_enum = SAEnum(
    CarType,
    name="cartype",  # MUST match existing enum name
    # create_type=False,  # 🚨 important
    nullable=False,
)

if TYPE_CHECKING:
    from src.api.models import User


# ===============================
# Default Ride Setting Schema
# ===============================
class DefaultRideSetting(TimeStampedModel, table=True):
    __tablename__ = "default_ride_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
        foreign_key="users.id", description="User who posted the ride", unique=True
    )

    car_number: str = Field(description="Car registration number")
    car_pic: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="Car image"
    )

    seats_available: int = Field(ge=1, description="Available seats")
    price_per_seat: Optional[float] = Field(default=None)
    total_price: Optional[float] = Field(default=None)
    negotiable: Optional[bool] = Field(default=False)
    notes: Optional[str] = None

    car_type: CarType = Field(
        sa_column=Column(car_type_enum),
        description="Type of car",
    )
    car_name: str = Field(description="Car name / brand")
    car_model: Optional[str] = Field(default=None)

    active: bool = Field(default=True)

    user: Optional["User"] = Relationship()


class DefaultRideSettingForm:
    def __init__(
        self,
        car_number: Optional[str] = Form(None),
        car_type: Optional[str] = Form(None),
        car_name: Optional[str] = Form(None),
        car_model: Optional[str] = Form(None),
        notes: Optional[str] = Form(None),
        # Numeric fields
        seats_available: Optional[str] = Form(None),
        price_per_seat: Optional[str] = Form(None),
        total_price: Optional[str] = Form(None),
        # Boolean
        negotiable: Optional[bool] = Form(None),
        car_pic: Optional[Union[UploadFile, str]] = File(None),
    ):
        # Convert empty → None
        # Convert empty string → None
        def clean(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip() == "":
                return None
            return v

        # Convert "true"/"false"/"1"/"0" → boolean
        def to_bool(v):
            v = clean(v)
            if v is None:
                return None
            val = str(v).lower()
            if val in ["true", "1", "yes"]:
                return True
            if val in ["false", "0", "no"]:
                return False
            return None  # fallback

        # Convert to int
        def to_int(v):
            v = clean(v)
            if v is None:
                return None
            try:
                return int(v)
            except:
                return None

        # Convert to float
        def to_float(v):
            v = clean(v)
            if v is None:
                return None
            try:
                return float(v)
            except:
                return None

        # Assign fields

        self.car_number = clean(car_number)
        self.car_type = clean(car_type)
        self.car_name = clean(car_name)
        self.car_model = clean(car_model)

        self.notes = clean(notes)

        self.seats_available = to_int(seats_available)
        self.price_per_seat = to_float(price_per_seat)
        self.total_price = to_float(total_price)

        self.negotiable = to_bool(negotiable)
        self.car_pic = car_pic


class DefaultRideSettingUserRead(SQLModel):
    id: int
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None


class DefaultRideSettingRead(SQLModel, TimeStampReadModel):
    id: int
    user_id: int
    user: Optional[DefaultRideSettingUserRead] = None
    car_number: str
    car_pic: Optional[Dict[str, Any]] = None

    seats_available: int
    price_per_seat: Optional[float] = None
    total_price: Optional[float] = None

    negotiable: Optional[bool] = None
    notes: Optional[str] = None

    car_type: str
    car_name: str
    car_model: Optional[str] = None

    active: bool
