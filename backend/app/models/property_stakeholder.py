import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._enum_helper import enum_values


class StakeholderRoleInProperty(str, enum.Enum):
    OWNER = "owner"
    CO_OWNER = "co_owner"
    MORTGAGEE = "mortgagee"
    REIT_HOLDER = "reit_holder"
    INSURER = "insurer"
    DEVELOPER = "developer"
    CUSTODIAN = "custodian"


class PropertyStakeholder(Base):
    """
    Links a property to one of its commercial stakeholders. A flat owned by
    an individual, mortgaged to a bank, and packaged into a REIT trust will
    have three rows here — one per relationship.
    """

    __tablename__ = "property_stakeholders"
    __table_args__ = (
        UniqueConstraint(
            "property_id", "owner_profile_id", "role_in_property",
            name="uq_property_stakeholder_role",
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
    owner_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("owner_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role_in_property: Mapped[StakeholderRoleInProperty] = mapped_column(
        Enum(
            StakeholderRoleInProperty,
            name="stakeholder_role_in_property",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    share_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    property = relationship("Property", foreign_keys=[property_id])
    owner_profile = relationship("OwnerProfile", foreign_keys=[owner_profile_id])
