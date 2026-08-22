from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

SPECIAL_CHARS = set('$@#%_-/\\!&*+=?.,;:')

def check_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 64:
        raise ValueError("Password must be at most 64 characters long")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c in SPECIAL_CHARS for c in password):
        raise ValueError("Password must contain at least one special character ($ @ # % _ - / \\ ! & * + = ? . , ; :)")
    return password

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    admin_code: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return check_password_strength(v)

class UserLogin(BaseModel):
    username: str  # or email; up to you
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: str | None = None

class FriendUser(BaseModel):
    friendship_id: int
    id: int
    username: str
    email: str

class FriendsList(BaseModel):
    friends: list[FriendUser]
    incoming_requests: list[FriendUser]
    outgoing_requests: list[FriendUser]

class RespondRequest(BaseModel):
    action: str  # "accept" or "decline"