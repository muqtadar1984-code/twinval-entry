import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_intern_or_admin
from app.models.observation import ObservationEntry, ObservationType, Severity
from app.models.user import User
from app.schemas.common import Page
from app.schemas.observation import (
    ObservationListItem,
    ObservationOut,
    ObservationVerifyOut,
)
from app.services.access_control import observation_access_filter
from app.services.hash_chain import (
    NewEntryInput,
    insert_observation_atomic,
    verify_entry,
)
from app.services.storage import PhotoValidationError, upload_photo

router = APIRouter(prefix="/observations", tags=["observations"])


@router.post("", response_model=ObservationOut, status_code=status.HTTP_201_CREATED)
async def submit_observation(
    property_id: uuid.UUID = Form(...),
    sensor_zone_id: uuid.UUID = Form(...),
    observation_type: ObservationType = Form(...),
    description: str = Form(..., min_length=20, max_length=1000),
    severity: Severity = Form(...),
    photo: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_intern_or_admin),
):
    """
    Multipart submission. The photo file (if present) is validated and
    uploaded to S3 before the chain entry is inserted, so a failed upload
    cannot leave a chain row pointing at a non-existent object.
    """
    photo_url: Optional[str] = None
    if photo is not None and photo.filename:
        content = await photo.read()
        if content:
            try:
                result = upload_photo(content, photo.content_type or "application/octet-stream")
            except PhotoValidationError as e:
                raise HTTPException(status_code=400, detail=str(e))
            photo_url = result.public_url

    payload = NewEntryInput(
        intern_id=user.id,
        property_id=property_id,
        sensor_zone_id=sensor_zone_id,
        observation_type=observation_type,
        description=description,
        severity=severity,
        photo_url=photo_url,
    )

    try:
        entry = insert_observation_atomic(db, payload)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(entry)
    return entry


@router.get("", response_model=Page[ObservationListItem])
def list_observations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    severity: Optional[Severity] = None,
    property_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    base = select(ObservationEntry).where(observation_access_filter(db, user))

    if severity is not None:
        base = base.where(ObservationEntry.severity == severity)
    if property_id is not None:
        base = base.where(ObservationEntry.property_id == property_id)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()
    rows = (
        db.execute(
            base.order_by(ObservationEntry.chain_sequence.desc()).limit(limit).offset(offset)
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


@router.get("/{entry_id}", response_model=ObservationOut)
def get_observation(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.execute(
        select(ObservationEntry).where(
            and_(
                ObservationEntry.id == entry_id,
                observation_access_filter(db, user),
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="observation not found")
    return entry


@router.get("/{entry_id}/verify", response_model=ObservationVerifyOut)
def verify_observation(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.execute(
        select(ObservationEntry).where(
            and_(
                ObservationEntry.id == entry_id,
                observation_access_filter(db, user),
            )
        )
    ).scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="observation not found")

    result = verify_entry(db, entry)
    return ObservationVerifyOut(
        valid=result.valid,
        computed_hash=result.computed_hash,
        stored_hash=result.stored_hash,
        chain_intact=result.chain_intact,
    )
