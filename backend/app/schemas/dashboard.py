"""Pydantic models for the analytics dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.observation import Severity
from app.models.property import PropertyStatus
from app.models.stream import KycStatus, Stream


class DashboardZoneRow(BaseModel):
    """One row per sensor zone with property + owner + observation rollups."""

    model_config = ConfigDict(from_attributes=True)

    # Identity
    zone_id: uuid.UUID
    property_id: uuid.UUID
    owner_id: uuid.UUID

    # Stream + client
    stream: Stream
    owner_name: str
    kyc_status: KycStatus

    # Property
    property_name: str
    city: Optional[str]
    country: Optional[str]
    property_status: PropertyStatus
    land_value: Optional[Decimal]
    structure_value: Optional[Decimal]

    # Zone
    building_label: str
    zone_label: str
    zone_active: bool

    # Aggregates (live = non-voided)
    total_observations: int
    normal_count: int
    watch_count: int
    alert_count: int
    reviewed_count: int
    voided_count: int

    # Latest non-voided observation
    last_submitted_at: Optional[datetime]
    last_severity: Optional[Severity]
    last_submitted_by_name: Optional[str]
    days_since_last: Optional[int]


class DashboardResponse(BaseModel):
    """Response envelope: rows + summary counters of the filtered view."""

    rows: list[DashboardZoneRow]
    total_zones: int
    total_properties: int
    total_observations: int
    total_zones_unfiltered: int
    total_properties_unfiltered: int
    total_observations_unfiltered: int
