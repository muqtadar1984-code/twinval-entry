"""Activity dashboard — operational signals for admins."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.observation import ObservationType, Severity
from app.models.stream import Stream


class PendingReviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: uuid.UUID
    entry_ref_id: str
    submitted_at: datetime
    property_name: str
    building_label: str
    zone_label: str
    severity: Severity
    observation_type: ObservationType
    description_excerpt: str  # first 160 chars
    intern_name: str
    days_waiting: int


class StaleZoneItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone_id: uuid.UUID
    property_id: uuid.UUID
    property_name: str
    building_label: str
    zone_label: str
    owner_name: str
    stream: Stream
    last_submitted_at: Optional[datetime]
    days_stale: Optional[int]  # None if never observed
    never_observed: bool


class WeeklyBucket(BaseModel):
    week_start: date
    normal: int
    watch: int
    alert: int
    total: int


class PhotoCoverage(BaseModel):
    total_alerts: int
    alerts_with_photo: int
    alert_coverage_pct: float
    total_observations: int
    observations_with_photo: int
    overall_coverage_pct: float


class ActivityResponse(BaseModel):
    pending_review: list[PendingReviewItem]
    pending_review_total: int  # full count, even if list is truncated

    stale_zones: list[StaleZoneItem]
    stale_zones_total: int
    stale_threshold_days: int

    weekly_buckets: list[WeeklyBucket]

    photo_coverage: PhotoCoverage

    submissions_last_7_days: int
