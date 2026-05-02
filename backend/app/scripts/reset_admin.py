"""Reset the admin password from the current INITIAL_ADMIN_PASSWORD env var.

Use this when:
  - You changed INITIAL_ADMIN_PASSWORD in Railway but the existing admin
    user still has the old hash. The lifespan bootstrap is idempotent
    and does not update an existing user's password.
  - You forgot the admin password and need to set a known value.

Usage (from inside the container, e.g. via Railway shell):

    python -m app.scripts.reset_admin

Looks up the user by INITIAL_ADMIN_EMAIL first; if not found, falls back
to the first user with role=admin.
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth import hash_password


def main() -> int:
    settings = get_settings()
    new_password = settings.initial_admin_password
    target_email = settings.initial_admin_email

    if not new_password:
        print("INITIAL_ADMIN_PASSWORD is empty — set it in env and re-run.")
        return 2

    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.email == target_email)
        ).scalar_one_or_none()
        if user is None:
            user = db.execute(
                select(User).where(User.role == UserRole.ADMIN).limit(1)
            ).scalar_one_or_none()

        if user is None:
            print(
                "No admin user found. Restart the service so the lifespan "
                "bootstrap creates one from INITIAL_ADMIN_*."
            )
            return 1

        user.password_hash = hash_password(new_password)
        db.commit()
        print(f"Password reset for {user.email} (role={user.role.value}).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
