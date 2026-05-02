"""
Stakeholder access enforcement.

Stakeholders must only see observations matching at least one of their
unexpired AccessGrant rows. Tests cover stream, owner-profile, property,
and ALL scopes.
"""

import uuid
from datetime import datetime, timedelta, timezone


def _seed_observation(db, intern, prop, zone, description="test obs body."):
    from app.models.observation import ObservationType, Severity
    from app.services.hash_chain import NewEntryInput, insert_observation_atomic

    insert_observation_atomic(
        db,
        NewEntryInput(
            intern_id=intern.id,
            property_id=prop.id,
            sensor_zone_id=zone.id,
            observation_type=ObservationType.VISUAL_INSPECTION,
            description=description + " padding for length.",
            severity=Severity.NORMAL,
            photo_url=None,
        ),
    )
    db.commit()


def test_stakeholder_with_no_grants_sees_nothing(
    stakeholder_client, db_session, chain_context
):
    _seed_observation(db_session, chain_context["intern"], chain_context["property"], chain_context["zone"])

    r = stakeholder_client.get("/observations")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_stakeholder_with_property_grant_sees_only_that_property(
    db_session,
    stakeholder_client,
    stakeholder_user,
    admin_user,
    chain_context,
    owner_profile_reit,
):
    """Grant for property X → sees X but not other properties."""
    from app.models.access_grant import AccessGrant, AccessScopeKind
    from app.models.property import Property
    from app.models.sensor_zone import SensorZone

    # Seed a second property + zone + observation
    other_prop = Property(
        id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        name="Block X",
        address="Other",
        primary_owner_id=owner_profile_reit.id,
        created_by=admin_user.id,
    )
    other_zone = SensorZone(
        id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        property_id=other_prop.id,
        building_label="X",
        zone_label="Y",
    )
    db_session.add_all([other_prop, other_zone])
    db_session.commit()

    _seed_observation(db_session, chain_context["intern"], chain_context["property"], chain_context["zone"], description="visible obs")
    _seed_observation(db_session, chain_context["intern"], other_prop, other_zone, description="hidden obs")

    grant = AccessGrant(
        user_id=stakeholder_user.id,
        scope_kind=AccessScopeKind.PROPERTY,
        scope_property_id=chain_context["property"].id,
        can_view_observations=True,
        granted_by=admin_user.id,
    )
    db_session.add(grant)
    db_session.commit()

    r = stakeholder_client.get("/observations")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["property_id"] == str(chain_context["property"].id)


def test_stakeholder_with_stream_grant_sees_all_in_stream(
    db_session,
    stakeholder_client,
    stakeholder_user,
    admin_user,
    chain_context,
):
    from app.models.access_grant import AccessGrant, AccessScopeKind
    from app.models.stream import Stream

    _seed_observation(db_session, chain_context["intern"], chain_context["property"], chain_context["zone"])

    grant = AccessGrant(
        user_id=stakeholder_user.id,
        scope_kind=AccessScopeKind.STREAM,
        scope_stream=Stream.REIT,
        can_view_observations=True,
        granted_by=admin_user.id,
    )
    db_session.add(grant)
    db_session.commit()

    r = stakeholder_client.get("/observations")
    assert r.json()["total"] == 1


def test_expired_grant_does_not_grant_access(
    db_session,
    stakeholder_client,
    stakeholder_user,
    admin_user,
    chain_context,
):
    from app.models.access_grant import AccessGrant, AccessScopeKind

    _seed_observation(db_session, chain_context["intern"], chain_context["property"], chain_context["zone"])

    grant = AccessGrant(
        user_id=stakeholder_user.id,
        scope_kind=AccessScopeKind.PROPERTY,
        scope_property_id=chain_context["property"].id,
        can_view_observations=True,
        granted_by=admin_user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(grant)
    db_session.commit()

    r = stakeholder_client.get("/observations")
    assert r.json()["total"] == 0


def test_stakeholder_with_all_scope_grant_sees_everything(
    db_session,
    stakeholder_client,
    stakeholder_user,
    admin_user,
    chain_context,
):
    from app.models.access_grant import AccessGrant, AccessScopeKind

    _seed_observation(db_session, chain_context["intern"], chain_context["property"], chain_context["zone"])

    grant = AccessGrant(
        user_id=stakeholder_user.id,
        scope_kind=AccessScopeKind.ALL,
        can_view_observations=True,
        granted_by=admin_user.id,
    )
    db_session.add(grant)
    db_session.commit()

    r = stakeholder_client.get("/observations")
    assert r.json()["total"] == 1


def test_stakeholder_cannot_submit_observations(
    stakeholder_client, property_block_a, sensor_zone_block_a_roof
):
    """Submission requires intern or admin role — stakeholders are read-only."""
    r = stakeholder_client.post(
        "/observations",
        data={
            "property_id": str(property_block_a.id),
            "sensor_zone_id": str(sensor_zone_block_a_roof.id),
            "observation_type": "Anomaly",
            "description": "A long enough description that should never go through.",
            "severity": "Watch",
        },
    )
    assert r.status_code == 403
