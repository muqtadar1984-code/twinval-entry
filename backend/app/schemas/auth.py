import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    email: EmailStr
    role: str


class MeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
