from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.common import APIModel


class LoginRequest(APIModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class RegisterRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=160)


class UserOut(APIModel):
    id: uuid.UUID
    email: str
    name: str
    role: str


class AuthResponse(APIModel):
    token: str
    user: UserOut
