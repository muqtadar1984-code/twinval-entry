import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.stream import Stream


class AccessScopeKind(str, enum.Enum):
    ALL = "all"
    STREAM = "stream"
    OWNER_PROFILE = "owner_profile"
    PROPERTY = "property"


class AccessGrant(Base):
    """
    Authorisation rule. A user gets to see properties / observations
    matching the scope:

      ALL            → unrestricted (issued to admins, auditors)
      STREAM         → all properties whose primary owner is in this stream
      OWNER_PROFILE  → all properties owned by this counterparty
      PROPERTY       → just this one property

    Each grant carries permission flags. A user can hold multiple grants;
    effective permission is the union of all unexpired grants.
    """

    __tablename__ = "access_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    scope_kind: Mapped[AccessScopeKind] = mapped_column(
        Enum(AccessScopeKind, name="access_scope_kind"), nullable=False
    )
    scope_stream: Mapped[Stream | None] = mapped_column(
        Enum(Stream, name="stream"), nullable=True
    )
    scope_owner_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("owner_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scope_property_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    can_view_observations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_view_chain_audit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_view_financials: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_view_personal_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    granted_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])
