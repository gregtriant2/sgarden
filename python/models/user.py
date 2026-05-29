from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserInDB(BaseModel):
    """User document as stored in MongoDB."""

    id: Optional[str] = Field(None, alias="_id")
    username: str
    email: str
    password: str
    role: str = "user"
    last_active_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RegisterRequest(BaseModel):
    """Request body for registering a new user."""

    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """Request body for authenticating a user."""

    username: str
    password: str


class AuthResponse(BaseModel):
    """Authentication response containing the issued JWT and user info."""

    token: str
    username: str
    role: str
