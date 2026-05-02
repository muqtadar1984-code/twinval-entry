"""Idempotent first-boot setup."""

from __future__ import annotations

import logging

import sqlalchemy
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.user import User, UserRole
from app.services.auth import hash_password

log = logging.getLogger(__name__)


def ensure_initial_admin(db: Session) -> User | None:
    """
    Create the bootstrap admin user if no admin exists yet.

    Skips silently if:
      - the users table doesn't exist (migrations haven't run)
      - any admin already exists
      - the configured initial-admin email is already taken
    """
    bind = db.bind
    if bind is None:
        return None

    try:
        inspector = sqlalchemy.inspect(bind)
        if not inspector.has_table("users"):
            log.info("bootstrap: users table missing — skipping")
            return None
    except Exception as e:  # bind not connectable
        log.warning("bootstrap: inspector failed (%s) — skipping", e)
        return None

    existing_admin = db.execute(
        select(User).where(User.role == UserRole.ADMIN).limit(1)
    ).scalar_one_or_none()
    if existing_admin is not None:
        log.info("bootstrap: admin already exists — skipping")
        return existing_admin

    settings = get_settings()
    same_email = db.execute(
        select(User).where(User.email == settings.initial_admin_email)
    ).scalar_one_or_none()
    if same_email is not None:
        log.warning(
            "bootstrap: a non-admin user with email %s already exists — skipping",
            settings.initial_admin_email,
        )
        return None

    admin = User(
        name=settings.initial_admin_name,
        email=settings.initial_admin_email,
        role=UserRole.ADMIN,
        password_hash=hash_password(settings.initial_admin_password),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    log.info("bootstrap: created initial admin %s", admin.email)
    return admin
