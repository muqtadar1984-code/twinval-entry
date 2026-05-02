import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.property import PropertyStatus
from app.models.stream import Stream


class PropertyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: str = Field(min_length=2)
    city: Optional[str] = Field(default=None, max_length=120)
    country: Optional[str] = Field(default=None, max_length=80)
    geo_lat: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    geo_lng: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    structure_value: Optional[Decimal] = Field(default=None, ge=0)
    land_value: Optional[Decimal] = Field(default=None, ge=0)
    primary_owner_id: uuid.UUID


class PropertyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    structure_value: Optional[Decimal] = Field(default=None, ge=0)
    land_value: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[PropertyStatus] = None


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: str
    city: Optional[str]
    country: Optional[str]
    geo_lat: Optional[Decimal]
    geo_lng: Optional[Decimal]
    structure_value: Optional[Decimal]
    land_value: Optional[Decimal]
    primary_owner_id: uuid.UUID
    primary_owner_name: str
    primary_owner_stream: Stream
    status: PropertyStatus
    created_by: uuid.UUID
    created_at: datetime
