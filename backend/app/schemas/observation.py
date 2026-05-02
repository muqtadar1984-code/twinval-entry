import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.observation import ObservationType, Severity
from app.models.stream import Stream


class ObservationCreate(BaseModel):
    """
    Submitted as multipart/form-data alongside an optional `photo` file.
    The server enforces submitted_at — clients never supply it.
    """

    property_id: uuid.UUID
    sensor_zone_id: uuid.UUID
    observation_type: ObservationType
    description: str = Field(min_length=20, max_length=1000)
    severity: Severity


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_ref_id: str
    intern_id: uuid.UUID
    property_id: uuid.UUID
    sensor_zone_id: uuid.UUID
    owner_profile_id: uuid.UUID
    submitted_at: datetime

    property_name: str
    building_label: str
    zone_label: str
    owner_profile_name: str
    stream: Stream

    observation_type: ObservationType
    description: str
    severity: Severity
    photo_url: Optional[str]

    entry_hash: str
    prev_hash: str
    chain_sequence: int

    reviewed: bool
    reviewer_note: Optional[str]
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]


class ObservationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_ref_id: str
    submitted_at: datetime
    property_id: uuid.UUID
    property_name: str
    building_label: str
    zone_label: str
    owner_profile_name: str
    stream: Stream
    observation_type: ObservationType
    severity: Severity
    entry_hash: str
    chain_sequence: int
    reviewed: bool


class ObservationVerifyOut(BaseModel):
    valid: bool
    computed_hash: str
    stored_hash: str
    chain_intact: bool


class ReviewRequest(BaseModel):
    reviewer_note: Optional[str] = Field(default=None, max_length=2000)
