import os
import uuid
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force a SQLite test database before app modules import settings.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-please-do-not-use-in-prod")
os.environ.setdefault("SKIP_STARTUP_BOOTSTRAP", "1")

from app.database import Base, get_db  # noqa: E402
from app import models  # noqa: E402,F401  -- register tables on Base.metadata
from app.models.owner_profile import OwnerProfile  # noqa: E402
from app.models.property import Property  # noqa: E402
from app.models.sensor_zone import SensorZone  # noqa: E402
from app.models.stream import KycStatus, Stream  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # share one connection across threads (TestClient + test thread)
        future=True,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def app(db_session: Session):
    from app.main import create_app

    app_instance = create_app()

    def _override_get_db():
        yield db_session

    app_instance.dependency_overrides[get_db] = _override_get_db
    return app_instance


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def _bearer(user: User) -> dict:
    from app.services.auth import create_access_token

    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def intern_user(db_session: Session) -> User:
    from app.services.auth import hash_password

    user = User(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Intern",
        email="intern@example.com",
        role=UserRole.INTERN,
        password_hash=hash_password("intern-password-123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    from app.services.auth import hash_password

    user = User(
        id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        name="Test Admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        password_hash=hash_password("admin-password-123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def stakeholder_user(db_session: Session) -> User:
    from app.services.auth import hash_password

    user = User(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        name="Test Stakeholder",
        email="stakeholder@example.com",
        role=UserRole.STAKEHOLDER,
        password_hash=hash_password("stake-password-123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def intern_client(app, intern_user):
    from fastapi.testclient import TestClient

    return TestClient(app, headers=_bearer(intern_user))


@pytest.fixture
def admin_client(app, admin_user):
    from fastapi.testclient import TestClient

    return TestClient(app, headers=_bearer(admin_user))


@pytest.fixture
def stakeholder_client(app, stakeholder_user):
    from fastapi.testclient import TestClient

    return TestClient(app, headers=_bearer(stakeholder_user))


@pytest.fixture
def owner_profile_reit(db_session: Session) -> OwnerProfile:
    owner = OwnerProfile(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        stream=Stream.REIT,
        legal_name="Test REIT Trust",
        legal_id="REIT-001",
        contact_email="ops@testreit.example",
        kyc_status=KycStatus.VERIFIED,
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)
    return owner


@pytest.fixture
def property_block_a(
    db_session: Session,
    admin_user: User,
    owner_profile_reit: OwnerProfile,
) -> Property:
    prop = Property(
        id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        name="IIUM Block A",
        address="Jalan Gombak, 53100 Kuala Lumpur",
        city="Kuala Lumpur",
        country="Malaysia",
        primary_owner_id=owner_profile_reit.id,
        created_by=admin_user.id,
    )
    db_session.add(prop)
    db_session.commit()
    db_session.refresh(prop)
    return prop


@pytest.fixture
def sensor_zone_block_a_roof(
    db_session: Session, property_block_a: Property
) -> SensorZone:
    zone = SensorZone(
        id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        property_id=property_block_a.id,
        building_label="Block A",
        zone_label="Roof - HVAC",
    )
    db_session.add(zone)
    db_session.commit()
    db_session.refresh(zone)
    return zone


@pytest.fixture
def chain_context(
    intern_user: User,
    property_block_a: Property,
    sensor_zone_block_a_roof: SensorZone,
    owner_profile_reit: OwnerProfile,
):
    """Bundle every reference an observation insert needs."""
    return {
        "intern": intern_user,
        "property": property_block_a,
        "zone": sensor_zone_block_a_roof,
        "owner": owner_profile_reit,
    }
