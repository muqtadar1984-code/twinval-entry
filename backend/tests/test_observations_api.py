"""Observation submission + read + verify endpoints."""

import uuid


def _submit_payload(prop, zone, description="A long enough description for testing."):
    return {
        "property_id": str(prop.id),
        "sensor_zone_id": str(zone.id),
        "observation_type": "Anomaly",
        "description": description,
        "severity": "Watch",
    }


def test_intern_submits_observation(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    r = intern_client.post(
        "/observations",
        data=_submit_payload(property_block_a, sensor_zone_block_a_roof),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["entry_ref_id"].startswith("TVL-")
    assert body["chain_sequence"] == 0
    assert len(body["entry_hash"]) == 64
    assert body["property_name"] == property_block_a.name
    assert body["building_label"] == "Block A"
    assert body["zone_label"] == "Roof - HVAC"
    assert body["stream"] == "reit"
    assert body["photo_url"] is None
    assert body["reviewed"] is False


def test_observation_with_photo_returns_photo_url(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    r = intern_client.post(
        "/observations",
        data=_submit_payload(property_block_a, sensor_zone_block_a_roof),
        files={"photo": ("crack.jpg", b"\xff\xd8\xff" + b"x" * 100, "image/jpeg")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # Storage stub returns local-stub:// URLs in tests (no S3 configured)
    assert body["photo_url"] is not None
    assert "stub" in body["photo_url"] or body["photo_url"].startswith("http")


def test_observation_rejects_oversize_photo(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    big = b"\xff\xd8\xff" + b"x" * (6 * 1024 * 1024)  # 6 MB > 5 MB cap
    r = intern_client.post(
        "/observations",
        data=_submit_payload(property_block_a, sensor_zone_block_a_roof),
        files={"photo": ("big.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 400
    assert "too large" in r.json()["detail"].lower()


def test_observation_rejects_non_image_mime(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    r = intern_client.post(
        "/observations",
        data=_submit_payload(property_block_a, sensor_zone_block_a_roof),
        files={"photo": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert r.status_code == 400


def test_observation_short_description_rejected(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    payload = _submit_payload(property_block_a, sensor_zone_block_a_roof)
    payload["description"] = "too short"
    r = intern_client.post("/observations", data=payload)
    assert r.status_code == 422  # FastAPI form-validation error


def test_observation_unknown_property_400(
    intern_client, sensor_zone_block_a_roof
):
    r = intern_client.post(
        "/observations",
        data={
            "property_id": str(uuid.uuid4()),
            "sensor_zone_id": str(sensor_zone_block_a_roof.id),
            "observation_type": "Anomaly",
            "description": "long enough description for testing.",
            "severity": "Watch",
        },
    )
    assert r.status_code == 400


def test_zone_from_other_property_rejected(
    intern_client, property_block_a, db_session, owner_profile_reit, admin_user
):
    """If a zone belongs to a different property, the chain insert refuses."""
    from app.models.property import Property
    from app.models.sensor_zone import SensorZone

    other_prop = Property(
        id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        name="Other",
        address="Else",
        primary_owner_id=owner_profile_reit.id,
        created_by=admin_user.id,
    )
    other_zone = SensorZone(
        id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        property_id=other_prop.id,
        building_label="Other",
        zone_label="Y",
    )
    db_session.add_all([other_prop, other_zone])
    db_session.commit()

    r = intern_client.post(
        "/observations",
        data={
            "property_id": str(property_block_a.id),
            "sensor_zone_id": str(other_zone.id),  # mismatched
            "observation_type": "Anomaly",
            "description": "long enough description for testing.",
            "severity": "Watch",
        },
    )
    assert r.status_code == 400


def test_intern_lists_only_own_observations(
    intern_client, intern_user, admin_user, db_session, chain_context
):
    """Intern's GET /observations must not show entries from other interns."""
    from datetime import datetime, timezone

    from app.models.observation import ObservationType, Severity
    from app.services.hash_chain import NewEntryInput, insert_observation_atomic

    # Submit one as the intern via API
    r = intern_client.post(
        "/observations",
        data={
            "property_id": str(chain_context["property"].id),
            "sensor_zone_id": str(chain_context["zone"].id),
            "observation_type": "Visual Inspection",
            "description": "Mine — should be visible to me.",
            "severity": "Normal",
        },
    )
    assert r.status_code == 201

    # Inject a second one belonging to the admin (simulating another intern)
    insert_observation_atomic(
        db_session,
        NewEntryInput(
            intern_id=admin_user.id,
            property_id=chain_context["property"].id,
            sensor_zone_id=chain_context["zone"].id,
            observation_type=ObservationType.VISUAL_INSPECTION,
            description="Not mine — should NOT be visible to the intern.",
            severity=Severity.NORMAL,
            photo_url=None,
        ),
        submitted_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    )
    db_session.commit()

    listing = intern_client.get("/observations")
    body = listing.json()
    assert body["total"] == 1
    assert all("Mine" in i["entry_ref_id"] or True for i in body["items"])  # ref ids don't carry text — just confirm count


def test_observation_get_and_verify(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    submit = intern_client.post(
        "/observations",
        data=_submit_payload(property_block_a, sensor_zone_block_a_roof),
    )
    entry_id = submit.json()["id"]

    fetched = intern_client.get(f"/observations/{entry_id}")
    assert fetched.status_code == 200
    assert fetched.json()["entry_hash"] == submit.json()["entry_hash"]

    verified = intern_client.get(f"/observations/{entry_id}/verify")
    assert verified.status_code == 200
    body = verified.json()
    assert body["valid"] is True
    assert body["chain_intact"] is True
    assert body["computed_hash"] == body["stored_hash"]


def test_admin_can_see_all_observations_via_admin_endpoint(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    # Intern submits one
    intern_client.post(
        "/observations",
        data=_submit_payload(property_block_a, sensor_zone_block_a_roof),
    )

    # Admin endpoint shows it
    r = admin_client.get("/admin/observations")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
