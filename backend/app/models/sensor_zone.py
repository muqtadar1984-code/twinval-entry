import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SensorZone(Base):
    """
    A monitored zone within a property. A zone is the smallest unit an
    intern observation can be anchored to. Examples:
      property "IIUM Block A" → building_label "Block A" → zone_label "Roof - HVAC"
      property "IIUM Block A" → building_label "Block A" → zone_label "Floor 3 - Lab"
    """

    __tablename__ = "sensor_zones"
    __table_args__ = (
        UniqueConstraint(
            "property_id", "building_label", "zone_label",
            name="uq_sensor_zone",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    building_label: Mapped[str] = mapped_column(String(120), nullable=False)
    zone_label: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    property = relationship("Property", foreign_keys=[property_id])
