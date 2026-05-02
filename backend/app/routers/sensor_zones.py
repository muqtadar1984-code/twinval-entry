import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin, require_intern_or_admin
from app.models.property import Property
from app.models.sensor_zone import SensorZone
from app.models.user import User
from app.schemas.common import Page
from app.schemas.sensor_zone import SensorZoneCreate, SensorZoneOut, SensorZoneUpdate

router = APIRouter(prefix="/sensor-zones", tags=["sensor-zones"])


@router.post("", response_model=SensorZoneOut, status_code=status.HTTP_201_CREATED)
def create_sensor_zone(
    body: SensorZoneCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_intern_or_admin),
):
    prop = db.get(Property, body.property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="property_id not found")

    zone = SensorZone(
        property_id=prop.id,
        building_label=body.building_label,
        zone_label=body.zone_label,
    )
    db.add(zone)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="zone with this building_label + zone_label already exists for the property",
        )
    db.refresh(zone)
    return zone


@router.get("", response_model=Page[SensorZoneOut])
def list_sensor_zones(
    property_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    base = select(SensorZone).where(SensorZone.property_id == property_id)
    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    rows = (
        db.execute(
            base.order_by(SensorZone.building_label.asc(), SensorZone.zone_label.asc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return Page[SensorZoneOut](
        items=[SensorZoneOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/{zone_id}", response_model=SensorZoneOut)
def update_sensor_zone(
    zone_id: uuid.UUID,
    body: SensorZoneUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    zone = db.get(SensorZone, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="sensor zone not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(zone, field, value)
    db.commit()
    db.refresh(zone)
    return zone
