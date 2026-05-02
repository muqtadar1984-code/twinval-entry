"""initial schema

users, owner_profiles, properties, property_stakeholders, sensor_zones,
observation_entries (with FKs + frozen snapshot fields), access_grants.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STREAM_VALUES = (
    "reit",
    "lender",
    "individual",
    "insurer",
    "government",
    "family_office",
    "developer",
)


def upgrade() -> None:
    # ---- users ---------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("intern", "admin", "stakeholder", "auditor", name="user_role"),
            nullable=False,
            server_default="intern",
        ),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ---- owner_profiles ------------------------------------------------
    op.create_table(
        "owner_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "stream",
            sa.Enum(*STREAM_VALUES, name="stream"),
            nullable=False,
        ),
        sa.Column("legal_name", sa.String(200), nullable=False),
        sa.Column("legal_id", sa.String(80), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(40), nullable=True),
        sa.Column(
            "kyc_status",
            sa.Enum("pending", "verified", "failed", name="kyc_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_owner_profiles_stream", "owner_profiles", ["stream"])
    op.create_index("ix_owner_profiles_legal_name", "owner_profiles", ["legal_name"])

    # ---- properties ----------------------------------------------------
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("country", sa.String(80), nullable=True),
        sa.Column("geo_lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("geo_lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("structure_value", sa.Numeric(15, 2), nullable=True),
        sa.Column("land_value", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "primary_owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "archived", name="property_status"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_properties_name", "properties", ["name"])
    op.create_index("ix_properties_primary_owner_id", "properties", ["primary_owner_id"])

    # ---- property_stakeholders ----------------------------------------
    op.create_table(
        "property_stakeholders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "role_in_property",
            sa.Enum(
                "owner",
                "co_owner",
                "mortgagee",
                "reit_holder",
                "insurer",
                "developer",
                "custodian",
                name="stakeholder_role_in_property",
            ),
            nullable=False,
        ),
        sa.Column("share_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "property_id", "owner_profile_id", "role_in_property",
            name="uq_property_stakeholder_role",
        ),
    )
    op.create_index("ix_property_stakeholders_property_id", "property_stakeholders", ["property_id"])
    op.create_index("ix_property_stakeholders_owner_profile_id", "property_stakeholders", ["owner_profile_id"])

    # ---- sensor_zones --------------------------------------------------
    op.create_table(
        "sensor_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("building_label", sa.String(120), nullable=False),
        sa.Column("zone_label", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "property_id", "building_label", "zone_label",
            name="uq_sensor_zone",
        ),
    )
    op.create_index("ix_sensor_zones_property_id", "sensor_zones", ["property_id"])

    # ---- observation_entries ------------------------------------------
    op.create_table(
        "observation_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entry_ref_id", sa.String(40), nullable=False),
        sa.Column(
            "intern_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "sensor_zone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sensor_zones.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "owner_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        # Frozen snapshots
        sa.Column("property_name", sa.String(200), nullable=False),
        sa.Column("building_label", sa.String(120), nullable=False),
        sa.Column("zone_label", sa.String(120), nullable=False),
        sa.Column("owner_profile_name", sa.String(200), nullable=False),
        sa.Column(
            "stream",
            sa.Enum(*STREAM_VALUES, name="stream"),
            nullable=False,
        ),
        sa.Column(
            "observation_type",
            sa.Enum(
                "Anomaly",
                "Maintenance Event",
                "Visual Inspection",
                "Sensor Health",
                name="observation_type",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "severity",
            sa.Enum("Normal", "Watch", "Alert", name="severity"),
            nullable=False,
        ),
        sa.Column("photo_url", sa.String(1024), nullable=True),
        sa.Column("entry_hash", sa.String(64), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("chain_sequence", sa.Integer, nullable=False),
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("reviewer_note", sa.Text, nullable=True),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("entry_ref_id", name="uq_observation_entry_ref_id"),
        sa.UniqueConstraint("entry_hash", name="uq_observation_entry_hash"),
        sa.UniqueConstraint("chain_sequence", name="uq_observation_chain_sequence"),
    )
    op.create_index("ix_observation_entry_ref_id", "observation_entries", ["entry_ref_id"])
    op.create_index("ix_observation_intern_id", "observation_entries", ["intern_id"])
    op.create_index("ix_observation_property_id", "observation_entries", ["property_id"])
    op.create_index("ix_observation_owner_profile_id", "observation_entries", ["owner_profile_id"])
    op.create_index("ix_observation_submitted_at", "observation_entries", ["submitted_at"])
    op.create_index("ix_observation_severity", "observation_entries", ["severity"])
    op.create_index("ix_observation_stream", "observation_entries", ["stream"])
    op.create_index("ix_observation_chain_sequence", "observation_entries", ["chain_sequence"])

    # ---- access_grants -------------------------------------------------
    op.create_table(
        "access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scope_kind",
            sa.Enum(
                "all", "stream", "owner_profile", "property",
                name="access_scope_kind",
            ),
            nullable=False,
        ),
        sa.Column(
            "scope_stream",
            sa.Enum(*STREAM_VALUES, name="stream"),
            nullable=True,
        ),
        sa.Column(
            "scope_owner_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("owner_profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "scope_property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("can_view_observations", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("can_view_chain_audit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("can_view_financials", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("can_view_personal_data", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "granted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_access_grants_user_id", "access_grants", ["user_id"])
    op.create_index("ix_access_grants_scope_owner_profile_id", "access_grants", ["scope_owner_profile_id"])
    op.create_index("ix_access_grants_scope_property_id", "access_grants", ["scope_property_id"])


def downgrade() -> None:
    op.drop_index("ix_access_grants_scope_property_id", table_name="access_grants")
    op.drop_index("ix_access_grants_scope_owner_profile_id", table_name="access_grants")
    op.drop_index("ix_access_grants_user_id", table_name="access_grants")
    op.drop_table("access_grants")
    op.execute("DROP TYPE IF EXISTS access_scope_kind")

    op.drop_index("ix_observation_chain_sequence", table_name="observation_entries")
    op.drop_index("ix_observation_stream", table_name="observation_entries")
    op.drop_index("ix_observation_severity", table_name="observation_entries")
    op.drop_index("ix_observation_submitted_at", table_name="observation_entries")
    op.drop_index("ix_observation_owner_profile_id", table_name="observation_entries")
    op.drop_index("ix_observation_property_id", table_name="observation_entries")
    op.drop_index("ix_observation_intern_id", table_name="observation_entries")
    op.drop_index("ix_observation_entry_ref_id", table_name="observation_entries")
    op.drop_table("observation_entries")
    op.execute("DROP TYPE IF EXISTS severity")
    op.execute("DROP TYPE IF EXISTS observation_type")

    op.drop_index("ix_sensor_zones_property_id", table_name="sensor_zones")
    op.drop_table("sensor_zones")

    op.drop_index("ix_property_stakeholders_owner_profile_id", table_name="property_stakeholders")
    op.drop_index("ix_property_stakeholders_property_id", table_name="property_stakeholders")
    op.drop_table("property_stakeholders")
    op.execute("DROP TYPE IF EXISTS stakeholder_role_in_property")

    op.drop_index("ix_properties_primary_owner_id", table_name="properties")
    op.drop_index("ix_properties_name", table_name="properties")
    op.drop_table("properties")
    op.execute("DROP TYPE IF EXISTS property_status")

    op.drop_index("ix_owner_profiles_legal_name", table_name="owner_profiles")
    op.drop_index("ix_owner_profiles_stream", table_name="owner_profiles")
    op.drop_table("owner_profiles")
    op.execute("DROP TYPE IF EXISTS kyc_status")
    op.execute("DROP TYPE IF EXISTS stream")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
