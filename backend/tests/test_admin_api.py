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
