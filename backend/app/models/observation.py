import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._enum_helper import enum_values
from app.models.stream import Stream


class ObservationType(str, enum.Enum):
    ANOMALY = "Anomaly"
    MAINTENANCE_EVENT = "Maintenance Event"
    VISUAL_INSPECTION = "Visual Inspection"
    SENSOR_HEALTH = "Sensor Health"


class Severity(str, enum.Enum):
    NORMAL = "Normal"
    WATCH = "Watch"
    ALERT = "Alert"


class ObservationEntry(Base):
    """
    A timestamped, hash-chained intern observation.

    The row carries both:
      - foreign keys (intern_id, property_id, sensor_zone_id, owner_profile_id),
        which let the chain be replayed against current data
      - frozen snapshot fields (property_name, building_label, zone_label,
        owner_profile_name, stream), which keep the audit log self-contained
        even if upstream rows are renamed or archived

    Both are part of the canonical hash payload.
    """

    __tablename__ = "observation_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entry_ref_id: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, index=True
    )

    intern_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sensor_zone_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sensor_zones.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("owner_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Frozen snapshots — written once at submission time, never updated.
    property_name: Mapped[str] = mapped_column(String(200), nullable=False)
    building_label: Mapped[str] = mapped_column(String(120), nullable=False)
    zone_label: Mapped[str] = mapped_column(String(120), nullable=False)
    owner_profile_name: Mapped[str] = mapped_column(String(200), nullable=False)
    stream: Mapped[Stream] = mapped_column(
        Enum(Stream, name="stream", values_callable=enum_values),
        nullable=False,
        index=True,
    )

    observation_type: Mapped[ObservationType] = mapped_column(
        Enum(ObservationType, name="observation_type", values_callable=enum_values),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    entry_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_sequence: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )

    reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    intern = relationship("User", foreign_keys=[intern_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    property = relationship("Property", foreign_keys=[property_id])
    sensor_zone = relationship("SensorZone", foreign_keys=[sensor_zone_id])
    owner_profile = relationship("OwnerProfile", foreign_keys=[owner_profile_id])
