from datetime import datetime
from enum import Enum
from enum import Enum
import json
from typing import TYPE_CHECKING, Annotated, Any, Dict, List, Literal, Optional, Union

from fastapi import File, Form, UploadFile
from pydantic import (
    BaseModel,
    EmailStr,
)

from sqlmodel import JSON, Column, Field, Index, Relationship, SQLModel, text
from src.api.models.mediaModel import MediaRead
from src.api.core.response import api_response
from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel
from src.api.models.roleModel import RoleRead

if TYPE_CHECKING:
    from src.api.models import User


class CarType(str, Enum):
    sedan = "sedan"
    hatchback = "hatchback"
    suv = "suv"
    crossover = "crossover"
    coupe = "coupe"
    convertible = "convertible"
    pickup = "pickup"
    van = "van"
    wagon = "wagon"
    minivan = "minivan"
    jeep = "jeep"
    other = "other"


# ===============================
# Location Schema (GeoJSON style)
# ===============================
class Location(SQLModel):
    type: str = Field(default="Point", const=True)
    coordinates: List[float] = Field(
        sa_column=Column(JSON), description="Coordinates [longitude, latitude]"
    )


# ===============================
# Ride Schema
# ===============================
class Ride(TimeStampedModel, table=True):
    __tablename__ = "rides"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", description="User who posted the ride")

    from_location: Location = Field(
        sa_column=Column(JSON), description="Origin location (GeoJSON)"
    )
    to_location: Location = Field(
        sa_column=Column(JSON), description="Destination location (GeoJSON)"
    )

    from_address: str = Field(index=True, description="Origin address string")
    to_address: str = Field(index=True, description="Destination address string")

    arrival_time: datetime = Field(description="Arrival time of ride")

    car_number: str = Field(description="Car registration number")
    car_pic: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="Car image"
    )
    other_images: Optional[List[Dict[str, Any]]] = Field(
        default=None, sa_column=Column(JSON), description="Other images of the car"
    )

    seats_available: int = Field(ge=1, description="Available seats")
    price_per_seat: Optional[float] = Field(default=None)
    total_price: Optional[float] = Field(default=None)
    negotiable: Optional[bool] = Field(default=False)
    notes: Optional[str] = None

    car_type: CarType = Field(description="Type of car")
    car_name: str = Field(description="Car name / brand")
    car_model: Optional[str] = Field(default=None)

    active: bool = Field(default=True)

    user: Optional["User"] = Relationship(back_populates="rides")


class UserRideForm:
    def __init__(
        self,
        # JSON (string in form-data)
        from_: Optional[str] = Form(None),
        to_: Optional[str] = Form(None),
        # Text fields
        from_address: Optional[str] = Form(None),
        to_address: Optional[str] = Form(None),
        arrival_time: Optional[str] = Form(None),
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
        active: Optional[bool] = Form(None),
        # file upload
        # ⬇️ FIX: Allow UploadFile OR empty string
        # File field
        car_pic: Optional[UploadFile] = File(None),
        other_images: List[UploadFile] = File(default=[]),  # ✅ Multiple files
        delete_images: Optional[List[str]] = Form(None),
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

        # Convert JSON string → dict
        def clean_json(v):

            v = clean(v)
            if v is None:
                return None
            try:
                return json.loads(v)
            except Exception:
                raise ValueError(f"Invalid JSON: {v}")

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

        self.from_ = clean_json(from_)
        self.to_ = clean_json(to_)

        self.from_address = clean(from_address)
        self.to_address = clean(to_address)

        self.arrival_time = clean(arrival_time)

        self.car_number = clean(car_number)
        self.car_type = clean(car_type)
        self.car_name = clean(car_name)
        self.car_model = clean(car_model)

        self.notes = clean(notes)

        self.seats_available = to_int(seats_available)
        self.price_per_seat = to_float(price_per_seat)
        self.total_price = to_float(total_price)

        self.negotiable = to_bool(negotiable)
        self.active = to_bool(active)

        # normalize empty string → None
        self.car_pic = car_pic

        # ✅ Better normalization
        self.other_images = other_images or []  # ✅ Simple fallback

        self.delete_images = clean(delete_images)


class LocationRead(BaseModel):
    type: str
    coordinates: List[float]


class RideRead(SQLModel, TimeStampReadModel):
    id: int

    user_id: int

    from_location: LocationRead
    to_location: LocationRead

    from_address: str
    to_address: str

    arrival_time: datetime

    car_number: str
    car_pic: Optional[MediaRead] = None
    other_images: Optional[List[MediaRead]] = None

    seats_available: int
    price_per_seat: Optional[float] = None
    total_price: Optional[float] = None

    negotiable: Optional[bool] = None
    notes: Optional[str] = None

    car_type: str
    car_name: str
    car_model: Optional[str] = None

    active: bool


class UserReadRide(SQLModel):
    id: int
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    verified: bool


class RideReadWithUser(RideRead):
    user: UserReadRide
