import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SensorZoneCreate(BaseModel):
    property_id: uuid.UUID
    building_label: str = Field(min_length=1, max_length=120)
    zone_label: str = Field(min_length=1, max_length=120)


class SensorZoneUpdate(BaseModel):
    building_label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    zone_label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    is_active: Optional[bool] = None


class SensorZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    building_label: str
    zone_label: str
    is_active: bool
    created_at: datetime
