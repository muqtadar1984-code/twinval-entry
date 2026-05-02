import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.stream import KycStatus, Stream


class OwnerProfileCreate(BaseModel):
    stream: Stream
    legal_name: str = Field(min_length=2, max_length=200)
    legal_id: Optional[str] = Field(default=None, max_length=80)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=40)


class OwnerProfileUpdate(BaseModel):
    legal_name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    legal_id: Optional[str] = Field(default=None, max_length=80)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(default=None, max_length=40)
    kyc_status: Optional[KycStatus] = None


class OwnerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stream: Stream
    legal_name: str
    legal_id: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    kyc_status: KycStatus
    created_at: datetime
