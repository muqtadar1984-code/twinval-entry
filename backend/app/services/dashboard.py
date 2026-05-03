"""
Analytics dashboard query.

Produces one row per sensor zone with:
  - the zone's property and primary owner
  - aggregated observation counts (live, by severity, reviewed, voided)
  - the latest non-voided submission's metadata

Filters narrow which zones appear (row inclusion). Aggregate counts are
always computed across ALL observations for the zones that survive the
filter — this matches the user's "pivot displaying counts" mental model.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.observation import ObservationEntry, Severity
from app.models.owner_profile import OwnerProfile
from app.models.property import Property, PropertyStatus
from app.models.sensor_zone import SensorZone
from app.models.stream import KycStatus, Stream
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, DashboardZoneRow


def _is_void_false(col):
    """SQLAlchemy expression for `voided = false`, dialect-portable."""
    return col == False  # noqa: E712 — explicit bool comparison for SQL


def fetch_dashboard(
    db: Session,
    *,
    streams: Optional[list[Stream]] = None,
    severities: Optional[list[Severity]] = None,
    property_status: Optional[PropertyStatus] = None,
    kyc_status: Optional[KycStatus] = None,
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
    search: Optional[str] = None,
) -> DashboardResponse:
    # ---------------------------------------------------------------
    # Aggregate counts per zone — across ALL observations on that zone.
    # ---------------------------------------------------------------
    not_voided = ObservationEntry.voided == False  # noqa: E712

    agg_q = (
        select(
            ObservationEntry.sensor_zone_id.label("zone_id"),
            func.coalesce(
                func.sum(case((not_voided, 1), else_=0)), 0
            ).label("total_obs"),
            func.coalesce(
                func.sum(case((and_(ObservationEntry.severity == Severity.NORMAL, not_voided), 1), else_=0)),
                0,
            ).label("normal_count"),
            func.coalesce(
                func.sum(case((and_(ObservationEntry.severity == Severity.WATCH, not_voided), 1), else_=0)),
                0,
            ).label("watch_count"),
            func.coalesce(
                func.sum(case((and_(ObservationEntry.severity == Severity.ALERT, not_voided), 1), else_=0)),
                0,
            ).label("alert_count"),
            func.coalesce(
                func.sum(case((and_(ObservationEntry.reviewed == True, not_voided), 1), else_=0)),  # noqa: E712
                0,
            ).label("reviewed_count"),
            func.coalesce(
                func.sum(case((ObservationEntry.voided == True, 1), else_=0)),  # noqa: E712
                0,
            ).label("voided_count"),
            func.max(case((not_voided, ObservationEntry.submitted_at))).label("last_submitted_at"),
        )
        .group_by(ObservationEntry.sensor_zone_id)
        .subquery()
    )

    # ---------------------------------------------------------------
    # Latest non-voided observation per zone (severity, intern).
    # ---------------------------------------------------------------
    ranked = (
        select(
            ObservationEntry.sensor_zone_id.label("zone_id"),
            ObservationEntry.severity.label("severity"),
            ObservationEntry.intern_id.label("intern_id"),
            ObservationEntry.submitted_at.label("submitted_at"),
            func.row_number()
            .over(
                partition_by=ObservationEntry.sensor_zone_id,
                order_by=ObservationEntry.submitted_at.desc(),
            )
            .label("rn"),
        )
        .where(not_voided)
        .subquery()
    )
    latest = (
        select(
            ranked.c.zone_id,
            ranked.c.severity,
            ranked.c.intern_id,
            ranked.c.submitted_at,
        )
        .where(ranked.c.rn == 1)
        .subquery()
    )

    Intern = aliased(User)

    # ---------------------------------------------------------------
    # Main query: zone × property × owner × aggregates × latest × intern
    # ---------------------------------------------------------------
    stmt = (
        select(
            SensorZone.id.label("zone_id"),
            SensorZone.building_label,
            SensorZone.zone_label,
            SensorZone.is_active.label("zone_active"),
            Property.id.label("property_id"),
            Property.name.label("property_name"),
            Property.city,
            Property.country,
            Property.status.label("property_status"),
            Property.land_value,
            Property.structure_value,
            OwnerProfile.id.label("owner_id"),
            OwnerProfile.legal_name.label("owner_name"),
            OwnerProfile.stream,
            OwnerProfile.kyc_status,
            agg_q.c.total_obs,
            agg_q.c.normal_count,
            agg_q.c.watch_count,
            agg_q.c.alert_count,
            agg_q.c.reviewed_count,
            agg_q.c.voided_count,
            agg_q.c.last_submitted_at,
            latest.c.severity.label("last_severity"),
            Intern.name.label("last_submitted_by_name"),
        )
        .select_from(SensorZone)
        .join(Property, SensorZone.property_id == Property.id)
        .join(OwnerProfile, Property.primary_owner_id == OwnerProfile.id)
        .outerjoin(agg_q, agg_q.c.zone_id == SensorZone.id)
        .outerjoin(latest, latest.c.zone_id == SensorZone.id)
        .outerjoin(Intern, Intern.id == latest.c.intern_id)
    )

    # ---------------------------------------------------------------
    # Filters (row inclusion)
    # ---------------------------------------------------------------
    if streams:
        stmt = stmt.where(OwnerProfile.stream.in_(streams))

    if property_status is not None:
        stmt = stmt.where(Property.status == property_status)

    if kyc_status is not None:
        stmt = stmt.where(OwnerProfile.kyc_status == kyc_status)

    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Property.name.ilike(like),
                OwnerProfile.legal_name.ilike(like),
                SensorZone.building_label.ilike(like),
                SensorZone.zone_label.ilike(like),
            )
        )

    # Severity filter: include zones with at least one matching live observation
    if severities:
        sev_zones = (
            select(ObservationEntry.sensor_zone_id)
            .where(not_voided, ObservationEntry.severity.in_(severities))
            .distinct()
            .subquery()
        )
        stmt = stmt.where(SensorZone.id.in_(select(sev_zones)))

    # Date range: include zones with at least one observation in window
    if submitted_from is not None or submitted_to is not None:
        date_zones_q = select(ObservationEntry.sensor_zone_id).where(not_voided)
        if submitted_from is not None:
            date_zones_q = date_zones_q.where(
                ObservationEntry.submitted_at >= submitted_from
            )
        if submitted_to is not None:
            date_zones_q = date_zones_q.where(
                ObservationEntry.submitted_at <= submitted_to
            )
        date_zones = date_zones_q.distinct().subquery()
        stmt = stmt.where(SensorZone.id.in_(select(date_zones)))

    stmt = stmt.order_by(
        OwnerProfile.legal_name.asc(),
        Property.name.asc(),
        SensorZone.building_label.asc(),
        SensorZone.zone_label.asc(),
    )

    rows_raw = db.execute(stmt).all()

    now = datetime.now(timezone.utc)
    rows: list[DashboardZoneRow] = []
    for r in rows_raw:
        last = r.last_submitted_at
        days_since = None
        if last is not None:
            last_aware = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
            days_since = max(0, math.floor((now - last_aware).total_seconds() / 86400))

        rows.append(
            DashboardZoneRow(
                zone_id=r.zone_id,
                property_id=r.property_id,
                owner_id=r.owner_id,
                stream=r.stream,
                owner_name=r.owner_name,
                kyc_status=r.kyc_status,
                property_name=r.property_name,
                city=r.city,
                country=r.country,
                property_status=r.property_status,
                land_value=r.land_value,
                structure_value=r.structure_value,
                building_label=r.building_label,
                zone_label=r.zone_label,
                zone_active=r.zone_active,
                total_observations=int(r.total_obs or 0),
                normal_count=int(r.normal_count or 0),
                watch_count=int(r.watch_count or 0),
                alert_count=int(r.alert_count or 0),
                reviewed_count=int(r.reviewed_count or 0),
                voided_count=int(r.voided_count or 0),
                last_submitted_at=last,
                last_severity=r.last_severity,
                last_submitted_by_name=r.last_submitted_by_name,
                days_since_last=days_since,
            )
        )

    # ---------------------------------------------------------------
    # Summary counts
    # ---------------------------------------------------------------
    distinct_property_ids = {row.property_id for row in rows}
    total_obs_filtered = sum(row.total_observations for row in rows) + sum(
        row.voided_count for row in rows
    )

    # Unfiltered totals across the system
    total_zones_unfiltered = db.execute(
        select(func.count(SensorZone.id))
    ).scalar_one()
    total_properties_unfiltered = db.execute(
        select(func.count(Property.id))
    ).scalar_one()
    total_observations_unfiltered = db.execute(
        select(func.count(ObservationEntry.id))
    ).scalar_one()

    return DashboardResponse(
        rows=rows,
        total_zones=len(rows),
        total_properties=len(distinct_property_ids),
        total_observations=total_obs_filtered,
        total_zones_unfiltered=total_zones_unfiltered,
        total_properties_unfiltered=total_properties_unfiltered,
        total_observations_unfiltered=total_observations_unfiltered,
    )
