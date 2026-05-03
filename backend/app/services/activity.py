"""
Activity dashboard service.

Builds a single response with the four operational signals an admin
wants on landing:
  - pending review queue (oldest unreviewed Watch / Alert entries)
  - stale zones (zones not observed in N days, or never)
  - weekly observation buckets for a 12-week trend chart
  - photo coverage (% of Alerts that have a photo attached)
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.observation import ObservationEntry, Severity
from app.models.owner_profile import OwnerProfile
from app.models.property import Property
from app.models.sensor_zone import SensorZone
from app.models.user import User
from app.schemas.activity import (
    ActivityResponse,
    PendingReviewItem,
    PhotoCoverage,
    StaleZoneItem,
    WeeklyBucket,
)


PENDING_REVIEW_LIMIT = 25
STALE_ZONES_LIMIT = 25
TREND_WEEKS = 12


def _description_excerpt(text: str, n: int = 160) -> str:
    text = text or ""
    if len(text) <= n:
        return text
    return text[: n - 1].rstrip() + "…"


def _week_start(d: datetime) -> date:
    """Monday of the ISO week for d (UTC)."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    d_utc = d.astimezone(timezone.utc).date()
    return d_utc - timedelta(days=d_utc.weekday())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def fetch_activity(
    db: Session,
    *,
    stale_threshold_days: int = 14,
) -> ActivityResponse:
    now = _now()

    # ---------------------------------------------------------------
    # 1. Pending review queue — Watch / Alert, not reviewed, not voided
    # ---------------------------------------------------------------
    pending_q = (
        select(ObservationEntry, User.name)
        .join(User, ObservationEntry.intern_id == User.id)
        .where(
            ObservationEntry.severity.in_([Severity.WATCH, Severity.ALERT]),
            ObservationEntry.reviewed == False,  # noqa: E712
            ObservationEntry.voided == False,  # noqa: E712
        )
        .order_by(ObservationEntry.submitted_at.asc())
    )
    pending_total = db.execute(
        select(func.count())
        .select_from(ObservationEntry)
        .where(
            ObservationEntry.severity.in_([Severity.WATCH, Severity.ALERT]),
            ObservationEntry.reviewed == False,  # noqa: E712
            ObservationEntry.voided == False,  # noqa: E712
        )
    ).scalar_one()

    pending_rows = db.execute(pending_q.limit(PENDING_REVIEW_LIMIT)).all()
    pending_items: list[PendingReviewItem] = []
    for entry, intern_name in pending_rows:
        submitted_aware = (
            entry.submitted_at
            if entry.submitted_at.tzinfo
            else entry.submitted_at.replace(tzinfo=timezone.utc)
        )
        days_waiting = max(0, math.floor((now - submitted_aware).total_seconds() / 86400))
        pending_items.append(
            PendingReviewItem(
                entry_id=entry.id,
                entry_ref_id=entry.entry_ref_id,
                submitted_at=entry.submitted_at,
                property_name=entry.property_name,
                building_label=entry.building_label,
                zone_label=entry.zone_label,
                severity=entry.severity,
                observation_type=entry.observation_type,
                description_excerpt=_description_excerpt(entry.description),
                intern_name=intern_name,
                days_waiting=days_waiting,
            )
        )

    # ---------------------------------------------------------------
    # 2. Stale zones — last live observation older than threshold,
    #    or never observed.
    # ---------------------------------------------------------------
    threshold = now - timedelta(days=stale_threshold_days)

    last_per_zone = (
        select(
            ObservationEntry.sensor_zone_id.label("zone_id"),
            func.max(ObservationEntry.submitted_at).label("last_at"),
        )
        .where(ObservationEntry.voided == False)  # noqa: E712
        .group_by(ObservationEntry.sensor_zone_id)
        .subquery()
    )

    zones_q = (
        select(
            SensorZone.id.label("zone_id"),
            SensorZone.building_label,
            SensorZone.zone_label,
            Property.id.label("property_id"),
            Property.name.label("property_name"),
            OwnerProfile.legal_name.label("owner_name"),
            OwnerProfile.stream,
            last_per_zone.c.last_at,
        )
        .select_from(SensorZone)
        .join(Property, SensorZone.property_id == Property.id)
        .join(OwnerProfile, Property.primary_owner_id == OwnerProfile.id)
        .outerjoin(last_per_zone, last_per_zone.c.zone_id == SensorZone.id)
        .where(
            or_(
                last_per_zone.c.last_at.is_(None),
                last_per_zone.c.last_at < threshold,
            )
        )
        .order_by(
            # Never-observed first, then oldest last_at first
            last_per_zone.c.last_at.is_(None).desc(),
            last_per_zone.c.last_at.asc().nullslast(),
        )
    )

    stale_total = db.execute(
        select(func.count())
        .select_from(SensorZone)
        .outerjoin(last_per_zone, last_per_zone.c.zone_id == SensorZone.id)
        .where(
            or_(
                last_per_zone.c.last_at.is_(None),
                last_per_zone.c.last_at < threshold,
            )
        )
    ).scalar_one()

    stale_rows = db.execute(zones_q.limit(STALE_ZONES_LIMIT)).all()
    stale_items: list[StaleZoneItem] = []
    for r in stale_rows:
        last_at = r.last_at
        days_stale = None
        never = last_at is None
        if last_at is not None:
            last_aware = (
                last_at if last_at.tzinfo else last_at.replace(tzinfo=timezone.utc)
            )
            days_stale = max(0, math.floor((now - last_aware).total_seconds() / 86400))
        stale_items.append(
            StaleZoneItem(
                zone_id=r.zone_id,
                property_id=r.property_id,
                property_name=r.property_name,
                building_label=r.building_label,
                zone_label=r.zone_label,
                owner_name=r.owner_name,
                stream=r.stream,
                last_submitted_at=last_at,
                days_stale=days_stale,
                never_observed=never,
            )
        )

    # ---------------------------------------------------------------
    # 3. Weekly buckets — last 12 ISO weeks, observations by severity.
    #    Bucket in Python so the SQL stays dialect-portable.
    # ---------------------------------------------------------------
    today = now.date()
    current_week_start = today - timedelta(days=today.weekday())
    earliest_week_start = current_week_start - timedelta(weeks=TREND_WEEKS - 1)
    earliest_dt = datetime.combine(earliest_week_start, datetime.min.time(), tzinfo=timezone.utc)

    week_rows = db.execute(
        select(
            ObservationEntry.submitted_at,
            ObservationEntry.severity,
        ).where(
            ObservationEntry.voided == False,  # noqa: E712
            ObservationEntry.submitted_at >= earliest_dt,
        )
    ).all()

    # Pre-seed all 12 weeks with zero counts so the chart never has gaps.
    weeks: dict[date, dict[str, int]] = {}
    for i in range(TREND_WEEKS):
        wk = earliest_week_start + timedelta(weeks=i)
        weeks[wk] = {"normal": 0, "watch": 0, "alert": 0}

    for submitted_at, severity in week_rows:
        wk = _week_start(submitted_at)
        if wk not in weeks:
            continue  # outside the trend window
        if severity == Severity.NORMAL:
            weeks[wk]["normal"] += 1
        elif severity == Severity.WATCH:
            weeks[wk]["watch"] += 1
        elif severity == Severity.ALERT:
            weeks[wk]["alert"] += 1

    weekly_buckets = [
        WeeklyBucket(
            week_start=wk,
            normal=counts["normal"],
            watch=counts["watch"],
            alert=counts["alert"],
            total=counts["normal"] + counts["watch"] + counts["alert"],
        )
        for wk, counts in sorted(weeks.items())
    ]

    # ---------------------------------------------------------------
    # 4. Photo coverage — % of live entries that have a photo URL.
    # ---------------------------------------------------------------
    base_obs_filter = ObservationEntry.voided == False  # noqa: E712
    has_photo = and_(
        ObservationEntry.photo_url.is_not(None),
        ObservationEntry.photo_url != "",
    )

    total_alerts = db.execute(
        select(func.count())
        .select_from(ObservationEntry)
        .where(base_obs_filter, ObservationEntry.severity == Severity.ALERT)
    ).scalar_one()

    alerts_with_photo = db.execute(
        select(func.count())
        .select_from(ObservationEntry)
        .where(
            base_obs_filter,
            ObservationEntry.severity == Severity.ALERT,
            has_photo,
        )
    ).scalar_one()

    total_obs = db.execute(
        select(func.count())
        .select_from(ObservationEntry)
        .where(base_obs_filter)
    ).scalar_one()

    obs_with_photo = db.execute(
        select(func.count())
        .select_from(ObservationEntry)
        .where(base_obs_filter, has_photo)
    ).scalar_one()

    alert_pct = (alerts_with_photo / total_alerts * 100.0) if total_alerts else 0.0
    overall_pct = (obs_with_photo / total_obs * 100.0) if total_obs else 0.0

    photo = PhotoCoverage(
        total_alerts=total_alerts,
        alerts_with_photo=alerts_with_photo,
        alert_coverage_pct=round(alert_pct, 1),
        total_observations=total_obs,
        observations_with_photo=obs_with_photo,
        overall_coverage_pct=round(overall_pct, 1),
    )

    # ---------------------------------------------------------------
    # 5. Submissions in the last 7 days.
    # ---------------------------------------------------------------
    seven_days_ago = now - timedelta(days=7)
    last_7 = db.execute(
        select(func.count())
        .select_from(ObservationEntry)
        .where(
            base_obs_filter,
            ObservationEntry.submitted_at >= seven_days_ago,
        )
    ).scalar_one()

    return ActivityResponse(
        pending_review=pending_items,
        pending_review_total=pending_total,
        stale_zones=stale_items,
        stale_zones_total=stale_total,
        stale_threshold_days=stale_threshold_days,
        weekly_buckets=weekly_buckets,
        photo_coverage=photo,
        submissions_last_7_days=last_7,
    )
