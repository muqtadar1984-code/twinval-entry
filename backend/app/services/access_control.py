"""
Access control / scope evaluation.

Roles:
  intern       — sees only observations they themselves submitted
  admin        — unrestricted
  auditor      — read-only across all observations and chain audits
  stakeholder  — scoped via AccessGrant rows (per stream / owner / property)

The observation_access_filter() helper returns a SQLAlchemy boolean clause
suitable for ORM filtering. Apply it to any list query to enforce scope.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import ColumnElement, false, or_, select, true
from sqlalchemy.orm import Session

from app.models.access_grant import AccessGrant, AccessScopeKind
from app.models.observation import ObservationEntry
from app.models.user import User, UserRole


def _active_grants(db: Session, user: User) -> list[AccessGrant]:
    now = datetime.now(timezone.utc)
    grants = (
        db.execute(select(AccessGrant).where(AccessGrant.user_id == user.id))
        .scalars()
        .all()
    )

    def _is_active(g: AccessGrant) -> bool:
        if g.expires_at is None:
            return True
        exp = g.expires_at
        # SQLite drops tz info on round-trip; normalise back to UTC.
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > now

    return [g for g in grants if _is_active(g)]


def observation_access_filter(db: Session, user: User) -> ColumnElement[bool]:
    """
    Return a where clause restricting observation_entries to those visible
    to `user`. Always combine with any other filters via and_(...).
    """
    if user.role == UserRole.ADMIN or user.role == UserRole.AUDITOR:
        return true()
    if user.role == UserRole.INTERN:
        return ObservationEntry.intern_id == user.id

    # stakeholder
    grants = [g for g in _active_grants(db, user) if g.can_view_observations]
    if not grants:
        return false()

    clauses = []
    for g in grants:
        if g.scope_kind == AccessScopeKind.ALL:
            return true()
        if g.scope_kind == AccessScopeKind.STREAM and g.scope_stream is not None:
            clauses.append(ObservationEntry.stream == g.scope_stream)
        elif (
            g.scope_kind == AccessScopeKind.OWNER_PROFILE
            and g.scope_owner_profile_id is not None
        ):
            clauses.append(
                ObservationEntry.owner_profile_id == g.scope_owner_profile_id
            )
        elif (
            g.scope_kind == AccessScopeKind.PROPERTY
            and g.scope_property_id is not None
        ):
            clauses.append(ObservationEntry.property_id == g.scope_property_id)

    return or_(*clauses) if clauses else false()


def can_view_chain_audit(db: Session, user: User) -> bool:
    if user.role in (UserRole.ADMIN, UserRole.AUDITOR):
        return True
    return any(
        g.can_view_chain_audit
        for g in _active_grants(db, user)
        if g.scope_kind == AccessScopeKind.ALL
    )


def can_enrol_properties(user: User) -> bool:
    """Interns and admins can enrol properties + zones + owner profiles."""
    return user.role in (UserRole.INTERN, UserRole.ADMIN)
