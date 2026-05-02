import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._enum_helper import enum_values
from app.models.stream import KycStatus, Stream


class OwnerProfile(Base):
    """A commercial counterparty — REIT fund, lender, individual owner, etc."""

    __tablename__ = "owner_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stream: Mapped[Stream] = mapped_column(
        Enum(Stream, name="stream", values_callable=enum_values),
        nullable=False,
        index=True,
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    legal_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    kyc_status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status", values_callable=enum_values),
        nullable=False,
        default=KycStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
