from pydantic import BaseModel, computed_field, Field
from datetime import datetime
from typing import Optional

# 50,000 characters ≈ 8,000–10,000 words — several times longer than any
# realistic accumulated notes, but small enough that nobody can use this field
# to dump megabytes into your database. Purely a technical ceiling, not a
# "stop talking" limit.
COMMENTS_MAX_LENGTH = 50_000

class BookCreate(BaseModel):
    title: str
    author: str
    year: int
    pages: int
    language: str = "Unknown"

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    pages: Optional[int] = None
    language: Optional[str] = None

class BookProgressUpdate(BaseModel):
    pages_read: int

class BookRatingUpdate(BaseModel):
    rating: float  # 0–10

class BookCommentUpdate(BaseModel):
    comments: str = Field(max_length=COMMENTS_MAX_LENGTH)

class BookOut(BaseModel):
    id: int
    title: str
    author: str
    year: int
    language: str
    pages: int
    pages_read: int
    rating: float
    comments: str
    created_at: datetime

    class Config:
        from_attributes = True

    @computed_field
    @property
    def reading_level(self) -> float:
        if not self.pages:
            return 0.0
        return round((self.pages_read / self.pages) * 100, 2)