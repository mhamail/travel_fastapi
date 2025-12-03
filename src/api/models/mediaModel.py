from typing import Optional

from pydantic import BaseModel, Field, field_serializer
from sqlmodel import SQLModel

from src.api.models.baseModel import TimeStampedModel
from src.config import DOMAIN


class Media(TimeStampedModel):
    __tablename__ = "media"
    id: int = Field(default=None, primary_key=True)
    filename: str = Field()
    extension: str = Field()
    original: str = Field()
    size_mb: Optional[float] = Field(default=None)
    thumbnail: Optional[str] = Field(default=None)
    media_type: str = Field()  # "image" | "video" | "doc"


class MediaRead(BaseModel):
    id: int
    filename: str
    extension: str
    original: str
    size_mb: Optional[float] = None
    thumbnail: Optional[str] = None
    media_type: str

    @field_serializer("original")
    def add_domain_to_url(self, v: Optional[str], _info):
        return f"{DOMAIN}{v}" if v else None

    @field_serializer("thumbnail")
    def add_domain_to_thumbnail(self, v: Optional[str], _info):
        return f"{DOMAIN}{v}" if v else None

    class Config:
        from_attributes = True
