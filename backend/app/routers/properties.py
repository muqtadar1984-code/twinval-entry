import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin, require_intern_or_admin
from app.models.access_grant import AccessGrant, AccessScopeKind
from app.models.observation import ObservationEntry
from app.models.owner_profile import OwnerProfile
from app.models.property import Property, PropertyStatus
from app.models.stream import Stream
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.property import PropertyCreate, PropertyOut, PropertyUpdate
from app.services.access_control import _active_grants

router = APIRouter(prefix="/properties", tags=["properties"])


def _to_out(prop: Property, owner: OwnerProfile) -> PropertyOut:
    return PropertyOut(
        id=prop.id,
        name=prop.name,
        address=prop.address,
        city=prop.city,
        country=prop.country,
        geo_lat=prop.geo_lat,
        geo_lng=prop.geo_lng,
        structure_value=prop.structure_value,
        land_value=prop.land_value,
        primary_owner_id=prop.primary_owner_id,
        primary_owner_name=owner.legal_name,
        primary_owner_stream=owner.stream,
        status=prop.status,
        created_by=prop.created_by,
        created_at=prop.created_at,
    )


def _property_access_filter(db: Session, user: User):
    if user.role in (UserRole.ADMIN, UserRole.AUDITOR):
        return None  # no filter
    if user.role == UserRole.INTERN:
        # Interns see properties they enrolled OR for which they have submitted observations.
        own_props = (
            select(ObservationEntry.property_id)
            .where(ObservationEntry.intern_id == user.id)
            .distinct()
        )
        return (Property.created_by == user.id) | Property.id.in_(own_props)

    # stakeholder
    grants = _active_grants(db, user)
    if not grants:
        return Property.id == uuid.UUID(int=0)  # always false

    clauses = []
    for g in grants:
        if g.scope_kind == AccessScopeKind.ALL:
            return None
        if g.scope_kind == AccessScopeKind.STREAM and g.scope_stream is not None:
            clauses.append(OwnerProfile.stream == g.scope_stream)
        elif g.scope_kind == AccessScopeKind.OWNER_PROFILE and g.scope_owner_profile_id is not None:
            clauses.append(Property.primary_owner_id == g.scope_owner_profile_id)
        elif g.scope_kind == AccessScopeKind.PROPERTY and g.scope_property_id is not None:
            clauses.append(Property.id == g.scope_property_id)

    if not clauses:
        return Property.id == uuid.UUID(int=0)
    from sqlalchemy import or_
    return or_(*clauses)


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(
    body: PropertyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_intern_or_admin),
):
    owner = db.get(OwnerProfile, body.primary_owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="primary_owner_id not found")

    prop = Property(
        name=body.name,
        address=body.address,
        city=body.city,
        country=body.country,
        geo_lat=body.geo_lat,
        geo_lng=body.geo_lng,
        structure_value=body.structure_value,
        land_value=body.land_value,
        primary_owner_id=owner.id,
        created_by=user.id,
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return _to_out(prop, owner)


@router.get("", response_model=Page[PropertyOut])
def list_properties(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    stream: Optional[Stream] = None,
    status_filter: Optional[PropertyStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    base = select(Property, OwnerProfile).join(
        OwnerProfile, Property.primary_owner_id == OwnerProfile.id
    )

    access_clause = _property_access_filter(db, user)
    if access_clause is not None:
        base = base.where(access_clause)
    if stream is not None:
        base = base.where(OwnerProfile.stream == stream)
    if status_filter is not None:
        base = base.where(Property.status == status_filter)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    rows = db.execute(
        base.order_by(Property.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return Page[PropertyOut](
        items=[_to_out(p, o) for (p, o) in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(
    property_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prop = db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="property not found")

    access_clause = _property_access_filter(db, user)
    if access_clause is not None:
        # Re-check with the access filter
        visible = db.execute(
            select(Property)
            .join(OwnerProfile, Property.primary_owner_id == OwnerProfile.id)
            .where(and_(Property.id == property_id, access_clause))
        ).scalar_one_or_none()
        if visible is None:
            raise HTTPException(status_code=403, detail="not authorised for this property")

    owner = db.get(OwnerProfile, prop.primary_owner_id)
    return _to_out(prop, owner)


@router.patch("/{property_id}", response_model=PropertyOut)
def update_property(
    property_id: uuid.UUID,
    body: PropertyUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    prop = db.get(Property, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="property not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prop, field, value)
    db.commit()
    db.refresh(prop)
    owner = db.get(OwnerProfile, prop.primary_owner_id)
    return _to_out(prop, owner)
