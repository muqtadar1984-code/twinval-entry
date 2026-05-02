import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._enum_helper import enum_values


class PropertyStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Property(Base):
    """
    A real-estate unit observed by the portal. The primary owner is the
    canonical counterparty for the chain snapshot, but a property can also
    have additional stakeholders (lender, REIT wrapper, insurer, ...) via
    PropertyStakeholder rows.
    """

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    geo_lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    geo_lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    structure_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    land_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

    primary_owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("owner_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus, name="property_status", values_callable=enum_values),
        nullable=False,
        default=PropertyStatus.ACTIVE,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    primary_owner = relationship("OwnerProfile", foreign_keys=[primary_owner_id])
    creator = relationship("User", foreign_keys=[created_by])
