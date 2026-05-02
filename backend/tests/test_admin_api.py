"""Admin endpoints: chain audit, review, user registration, access grants."""

import uuid


def test_chain_verify_empty(admin_client):
    r = admin_client.get("/admin/chain/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["total_entries"] == 0
    assert body["broken_links"] == []
    assert body["chain_valid"] is True


def test_chain_verify_with_entries(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    intern_client.post(
        "/observations",
        data={
            "property_id": str(property_block_a.id),
            "sensor_zone_id": str(sensor_zone_block_a_roof.id),
            "observation_type": "Anomaly",
            "description": "A long enough description for the audit walk.",
            "severity": "Watch",
        },
    )
    r = admin_client.get("/admin/chain/verify")
    body = r.json()
    assert body["total_entries"] == 1
    assert body["chain_valid"] is True


def test_admin_review_endpoint(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    submit = intern_client.post(
        "/observations",
        data={
            "property_id": str(property_block_a.id),
            "sensor_zone_id": str(sensor_zone_block_a_roof.id),
            "observation_type": "Anomaly",
            "description": "A long enough description for the review test.",
            "severity": "Alert",
        },
    )
    entry_id = submit.json()["id"]

    review = admin_client.patch(
        f"/admin/observations/{entry_id}/review",
        json={"reviewer_note": "Looks fine — closing."},
    )
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["reviewed"] is True
    assert body["reviewer_note"] == "Looks fine — closing."
    assert body["reviewed_by"] is not None
    assert body["reviewed_at"] is not None


def test_admin_register_user(admin_client):
    r = admin_client.post(
        "/admin/users",
        json={
            "name": "New Intern",
            "email": "newintern@example.com",
            "password": "fresh-password-123",
            "role": "intern",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "newintern@example.com"
    assert body["role"] == "intern"


def test_admin_register_duplicate_email_rejected(admin_client, intern_user):
    r = admin_client.post(
        "/admin/users",
        json={
            "name": "Duplicate",
            "email": intern_user.email,
            "password": "x" * 12,
            "role": "intern",
        },
    )
    assert r.status_code == 409


def test_intern_cannot_register_users(intern_client):
    r = intern_client.post(
        "/admin/users",
        json={
            "name": "Sneaky",
            "email": "sneaky@example.com",
            "password": "x" * 12,
            "role": "admin",
        },
    )
    assert r.status_code == 403


def test_admin_creates_property_scoped_access_grant(
    admin_client, stakeholder_user, property_block_a
):
    r = admin_client.post(
        "/admin/access-grants",
        json={
            "user_id": str(stakeholder_user.id),
            "scope_kind": "property",
            "scope_property_id": str(property_block_a.id),
            "can_view_observations": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["scope_kind"] == "property"
    assert body["scope_property_id"] == str(property_block_a.id)
    assert body["can_view_observations"] is True


def test_access_grant_validation_requires_matching_scope_field(admin_client, stakeholder_user):
    # scope_kind=stream without scope_stream → 422
    r = admin_client.post(
        "/admin/access-grants",
        json={
            "user_id": str(stakeholder_user.id),
            "scope_kind": "stream",
            # scope_stream missing
        },
    )
    assert r.status_code == 422


def test_admin_revokes_access_grant(
    admin_client, stakeholder_user, property_block_a
):
    create = admin_client.post(
        "/admin/access-grants",
        json={
            "user_id": str(stakeholder_user.id),
            "scope_kind": "property",
            "scope_property_id": str(property_block_a.id),
        },
    )
    grant_id = create.json()["id"]
    revoke = admin_client.delete(f"/admin/access-grants/{grant_id}")
    assert revoke.status_code == 204
    follow = admin_client.delete(f"/admin/access-grants/{grant_id}")
    assert follow.status_code == 404


# ---------------------------------------------------------------------------
# Void (audit-correct delete)
# ---------------------------------------------------------------------------


def _submit_one(intern_client, property_block_a, sensor_zone_block_a_roof):
    """Helper: submit a valid observation and return its JSON body."""
    r = intern_client.post(
        "/observations",
        data={
            "property_id": str(property_block_a.id),
            "sensor_zone_id": str(sensor_zone_block_a_roof.id),
            "observation_type": "Anomaly",
            "description": "Original entry to test the void workflow end-to-end.",
            "severity": "Watch",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_admin_voids_observation(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    entry = _submit_one(intern_client, property_block_a, sensor_zone_block_a_roof)
    original_hash = entry["entry_hash"]

    r = admin_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "Submitted in error during smoke test."},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["voided"] is True
    assert body["void_reason"] == "Submitted in error during smoke test."
    assert body["voided_by"] is not None
    assert body["voided_at"] is not None

    # CRITICAL: void must NOT mutate any chain-relevant field.
    assert body["entry_hash"] == original_hash
    assert body["prev_hash"] == entry["prev_hash"]
    assert body["chain_sequence"] == entry["chain_sequence"]


def test_void_does_not_break_chain_verification(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    entry = _submit_one(intern_client, property_block_a, sensor_zone_block_a_roof)
    admin_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "Test entry — voided to keep the live chain clean."},
    )

    # Per-entry verify still says the entry is valid.
    v = admin_client.get(f"/observations/{entry['id']}/verify")
    assert v.status_code == 200
    assert v.json()["valid"] is True
    assert v.json()["chain_intact"] is True

    # Full audit walk still says the chain is valid.
    audit = admin_client.get("/admin/chain/verify").json()
    assert audit["chain_valid"] is True
    assert audit["broken_links"] == []
    assert audit["total_entries"] == 1


def test_voiding_already_voided_returns_409(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    entry = _submit_one(intern_client, property_block_a, sensor_zone_block_a_roof)
    first = admin_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "First void of the smoke entry."},
    )
    assert first.status_code == 200

    second = admin_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "Trying to double-void."},
    )
    assert second.status_code == 409


def test_intern_cannot_void(
    intern_client, property_block_a, sensor_zone_block_a_roof
):
    entry = _submit_one(intern_client, property_block_a, sensor_zone_block_a_roof)
    r = intern_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "Trying to void my own entry as intern."},
    )
    assert r.status_code == 403


def test_void_requires_minimum_reason_length(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    entry = _submit_one(intern_client, property_block_a, sensor_zone_block_a_roof)
    r = admin_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "x"},
    )
    assert r.status_code == 422


def test_void_unknown_observation_returns_404(admin_client):
    r = admin_client.patch(
        f"/admin/observations/{uuid.uuid4()}/void",
        json={"reason": "Trying to void something that does not exist."},
    )
    assert r.status_code == 404
