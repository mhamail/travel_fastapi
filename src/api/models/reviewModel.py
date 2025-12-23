from typing import TYPE_CHECKING, Optional, Literal
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from src.api.models.userModel import UserRead
from src.api.models.baseModel import TimeStampReadModel, TimeStampedModel

if TYPE_CHECKING:
    from src.api.models import User


class Review(TimeStampedModel, table=True):
    __tablename__: Literal["reviews"] = "reviews"
    __table_args__ = (
        UniqueConstraint("reviewer_id", "target_id", name="uq_reviewer_target"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    reviewer_id: int = Field(foreign_key="users.id")
    target_id: int = Field(foreign_key="users.id")

    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None

    # relationships
    reviewer: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Review.reviewer_id]"}
    )
    target: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Review.target_id]"}
    )


class ReviewCreate(SQLModel):
    target_id: int
    rating: int
    comment: Optional[str] = None


class ReviewUpdate(SQLModel):
    rating: Optional[int] = None
    comment: Optional[str] = None


class ReviewRead(TimeStampReadModel):
    id: int
    rating: int
    comment: Optional[str] = None
    reviewer: Optional[UserRead] = None
    target: Optional[UserRead] = None

    class Config:
        from_attributes = True
