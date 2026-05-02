import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin, require_intern_or_admin
from app.models.owner_profile import OwnerProfile
from app.models.stream import Stream
from app.models.user import User
from app.schemas.common import Page
from app.schemas.owner_profile import (
    OwnerProfileCreate,
    OwnerProfileOut,
    OwnerProfileUpdate,
)

router = APIRouter(prefix="/owner-profiles", tags=["owner-profiles"])


@router.post("", response_model=OwnerProfileOut, status_code=status.HTTP_201_CREATED)
def create_owner_profile(
    body: OwnerProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_intern_or_admin),
):
    owner = OwnerProfile(
        stream=body.stream,
        legal_name=body.legal_name,
        legal_id=body.legal_id,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@router.get("", response_model=Page[OwnerProfileOut])
def list_owner_profiles(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    stream: Optional[Stream] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    base = select(OwnerProfile)
    if stream is not None:
        base = base.where(OwnerProfile.stream == stream)
    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    rows = (
        db.execute(
            base.order_by(OwnerProfile.legal_name.asc()).limit(limit).offset(offset)
        )
        .scalars()
        .all()
    )
    return Page[OwnerProfileOut](
        items=[OwnerProfileOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{owner_id}", response_model=OwnerProfileOut)
def get_owner_profile(
    owner_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    owner = db.get(OwnerProfile, owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="owner profile not found")
    return owner


@router.patch("/{owner_id}", response_model=OwnerProfileOut)
def update_owner_profile(
    owner_id: uuid.UUID,
    body: OwnerProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    owner = db.get(OwnerProfile, owner_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="owner profile not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(owner, field, value)
    db.commit()
    db.refresh(owner)
    return owner
