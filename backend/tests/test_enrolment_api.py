"""Property / owner / sensor-zone enrolment endpoints."""

import uuid


# ---------------------------------------------------------------------------
# Owner profiles
# ---------------------------------------------------------------------------


def test_intern_can_create_owner_profile(intern_client):
    r = intern_client.post(
        "/owner-profiles",
        json={
            "stream": "lender",
            "legal_name": "HDFC Bank Ltd",
            "legal_id": "L65920MH1994PLC080618",
            "contact_email": "ops@hdfc.example",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["stream"] == "lender"
    assert body["legal_name"] == "HDFC Bank Ltd"
    assert body["kyc_status"] == "pending"


def test_stakeholder_cannot_create_owner_profile(stakeholder_client):
    r = stakeholder_client.post(
        "/owner-profiles",
        json={"stream": "individual", "legal_name": "Jane Doe"},
    )
    assert r.status_code == 403


def test_unauthenticated_cannot_create_owner_profile(client):
    r = client.post(
        "/owner-profiles",
        json={"stream": "individual", "legal_name": "Jane Doe"},
    )
    assert r.status_code == 401


def test_list_owner_profiles_filters_by_stream(intern_client, owner_profile_reit):
    r = intern_client.get("/owner-profiles?stream=reit")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all(item["stream"] == "reit" for item in body["items"])


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


def test_intern_can_create_property(intern_client, owner_profile_reit):
    r = intern_client.post(
        "/properties",
        json={
            "name": "IIUM Block C",
            "address": "Jalan Gombak, Block C",
            "city": "Kuala Lumpur",
            "country": "Malaysia",
            "primary_owner_id": str(owner_profile_reit.id),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "IIUM Block C"
    assert body["primary_owner_name"] == owner_profile_reit.legal_name
    assert body["primary_owner_stream"] == "reit"
    assert body["status"] == "active"


def test_create_property_with_unknown_owner_404s(intern_client):
    r = intern_client.post(
        "/properties",
        json={
            "name": "Ghost Property",
            "address": "nowhere",
            "primary_owner_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 404


def test_admin_lists_all_properties(admin_client, property_block_a):
    r = admin_client.get("/properties")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    names = [p["name"] for p in body["items"]]
    assert "IIUM Block A" in names


def test_intern_only_sees_properties_they_enrolled(
    intern_client, intern_user, owner_profile_reit, property_block_a
):
    # property_block_a was created by admin_user — intern should NOT see it
    r = intern_client.get("/properties")
    assert r.status_code == 200
    body = r.json()
    ids = [p["id"] for p in body["items"]]
    assert str(property_block_a.id) not in ids

    # ...but if they enrol one themselves, they see it
    create = intern_client.post(
        "/properties",
        json={
            "name": "Intern's Property",
            "address": "Somewhere",
            "primary_owner_id": str(owner_profile_reit.id),
        },
    )
    assert create.status_code == 201

    r2 = intern_client.get("/properties")
    body2 = r2.json()
    ids2 = [p["id"] for p in body2["items"]]
    assert create.json()["id"] in ids2


# ---------------------------------------------------------------------------
# Sensor zones
# ---------------------------------------------------------------------------


def test_intern_can_create_sensor_zone(intern_client, property_block_a):
    r = intern_client.post(
        "/sensor-zones",
        json={
            "property_id": str(property_block_a.id),
            "building_label": "Block A",
            "zone_label": "Floor 2 - Lab",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["building_label"] == "Block A"
    assert body["is_active"] is True


def test_duplicate_sensor_zone_returns_409(intern_client, property_block_a):
    payload = {
        "property_id": str(property_block_a.id),
        "building_label": "Block A",
        "zone_label": "Lobby",
    }
    r1 = intern_client.post("/sensor-zones", json=payload)
    assert r1.status_code == 201
    r2 = intern_client.post("/sensor-zones", json=payload)
    assert r2.status_code == 409


def test_list_sensor_zones_for_property(intern_client, property_block_a, sensor_zone_block_a_roof):
    r = intern_client.get(f"/sensor-zones?property_id={property_block_a.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(z["zone_label"] == "Roof - HVAC" for z in body["items"])
