import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models.access_grant import AccessGrant
from app.models.observation import ObservationEntry, Severity
from app.models.stream import Stream
from app.models.user import User
from app.schemas.access_grant import AccessGrantCreate, AccessGrantOut
from app.schemas.chain_audit import ChainAuditOut
from app.schemas.common import Page
from app.schemas.observation import (
    ObservationListItem,
    ObservationOut,
    ReviewRequest,
)
from app.schemas.user import UserOut, UserRegisterRequest
from app.services.auth import hash_password
from app.services.hash_chain import verify_chain

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Observations — full unrestricted view + review action
# ---------------------------------------------------------------------------


@router.get("/observations", response_model=Page[ObservationListItem])
def list_all_observations(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    severity: Optional[Severity] = None,
    stream: Optional[Stream] = None,
    property_id: Optional[uuid.UUID] = None,
    intern_id: Optional[uuid.UUID] = None,
    submitted_from: Optional[datetime] = None,
    submitted_to: Optional[datetime] = None,
    reviewed: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    base = select(ObservationEntry)
    if severity is not None:
        base = base.where(ObservationEntry.severity == severity)
    if stream is not None:
        base = base.where(ObservationEntry.stream == stream)
    if property_id is not None:
        base = base.where(ObservationEntry.property_id == property_id)
    if intern_id is not None:
        base = base.where(ObservationEntry.intern_id == intern_id)
    if submitted_from is not None:
        base = base.where(ObservationEntry.submitted_at >= submitted_from)
    if submitted_to is not None:
        base = base.where(ObservationEntry.submitted_at <= submitted_to)
    if reviewed is not None:
        base = base.where(ObservationEntry.reviewed == reviewed)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    rows = (
        db.execute(
            base.order_by(ObservationEntry.chain_sequence.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return Page[ObservationListItem](
        items=[ObservationListItem.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/observations/{entry_id}/review", response_model=ObservationOut)
def review_observation(
    entry_id: uuid.UUID,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    entry = db.get(ObservationEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="observation not found")
    entry.reviewed = True
    entry.reviewer_note = body.reviewer_note
    entry.reviewed_by = admin.id
    entry.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# Chain audit
# ---------------------------------------------------------------------------


@router.get("/chain/verify", response_model=ChainAuditOut)
def admin_chain_verify(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    audit = verify_chain(db)
    return ChainAuditOut(
        total_entries=audit.total_entries,
        broken_links=audit.broken_links,
        chain_valid=audit.chain_valid,
    )


# ---------------------------------------------------------------------------
# User registration (admin creates intern / stakeholder accounts)
# ---------------------------------------------------------------------------


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    body: UserRegisterRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    existing = db.execute(
        select(User).where(User.email == body.email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    user = User(
        name=body.name,
        email=body.email,
        role=body.role,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=Page[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    base = select(User)
    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    rows = (
        db.execute(base.order_by(User.created_at.desc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return Page[UserOut](
        items=[UserOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Access grants — admin issues / revokes
# ---------------------------------------------------------------------------


@router.post(
    "/access-grants", response_model=AccessGrantOut, status_code=status.HTTP_201_CREATED
)
def create_access_grant(
    body: AccessGrantCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.get(User, body.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user_id not found")

    grant = AccessGrant(
        user_id=body.user_id,
        scope_kind=body.scope_kind,
        scope_stream=body.scope_stream,
        scope_owner_profile_id=body.scope_owner_profile_id,
        scope_property_id=body.scope_property_id,
        can_view_observations=body.can_view_observations,
        can_view_chain_audit=body.can_view_chain_audit,
        can_view_financials=body.can_view_financials,
        can_view_personal_data=body.can_view_personal_data,
        granted_by=admin.id,
        expires_at=body.expires_at,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


@router.get("/access-grants", response_model=Page[AccessGrantOut])
def list_access_grants(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    user_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    base = select(AccessGrant)
    if user_id is not None:
        base = base.where(AccessGrant.user_id == user_id)
    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    rows = (
        db.execute(
            base.order_by(AccessGrant.granted_at.desc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return Page[AccessGrantOut](
        items=[AccessGrantOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/access-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access_grant(
    grant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    grant = db.get(AccessGrant, grant_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="access grant not found")
    db.delete(grant)
    db.commit()
    return None
