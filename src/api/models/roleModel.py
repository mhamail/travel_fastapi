from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import JSON
from sqlmodel import Field, Relationship, SQLModel

from src.api.models.baseModel import TimeStampedModel, TimeStampReadModel

if TYPE_CHECKING:
    from src.api.models import User


class Role(TimeStampedModel, table=True):
    __tablename__ = "roles"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=50, unique=True)
    permissions: list[str] = Field(
        default_factory=list,
        sa_type=JSON,
    )
    users: List["User"] = Relationship(back_populates="role")


class RoleRead(TimeStampReadModel):
    id: int
    title: str
    permissions: list[str]


class RoleCreate(SQLModel):
    title: str
    permissions: list[str]


class RoleUpdate(SQLModel):
    title: Optional[str]
    permissions: Optional[list[str]]
