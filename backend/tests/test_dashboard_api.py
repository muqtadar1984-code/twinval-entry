"""Analytics dashboard endpoint."""

import uuid


def _submit_observation(intern_client, property_id, zone_id, severity="Normal", obs_type="Visual Inspection"):
    r = intern_client.post(
        "/observations",
        data={
            "property_id": str(property_id),
            "sensor_zone_id": str(zone_id),
            "observation_type": obs_type,
            "description": f"A {severity} entry for the dashboard test fixtures.",
            "severity": severity,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_dashboard_admin_only(intern_client):
    r = intern_client.get("/admin/dashboard/properties")
    assert r.status_code == 403


def test_dashboard_empty_state(admin_client):
    r = admin_client.get("/admin/dashboard/properties")
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] == []
    assert body["total_zones"] == 0
    assert body["total_properties"] == 0
    assert body["total_observations"] == 0
    assert body["total_zones_unfiltered"] == 0


def test_dashboard_zones_with_no_observations(
    admin_client, property_block_a, sensor_zone_block_a_roof
):
    r = admin_client.get("/admin/dashboard/properties")
    body = r.json()
    assert body["total_zones"] == 1
    assert body["total_properties"] == 1
    assert body["total_observations"] == 0

    row = body["rows"][0]
    assert row["property_name"] == property_block_a.name
    assert row["building_label"] == sensor_zone_block_a_roof.building_label
    assert row["total_observations"] == 0
    assert row["normal_count"] == 0
    assert row["watch_count"] == 0
    assert row["alert_count"] == 0
    assert row["voided_count"] == 0
    assert row["last_submitted_at"] is None
    assert row["last_severity"] is None
    assert row["last_submitted_by_name"] is None
    assert row["days_since_last"] is None


def test_dashboard_aggregates_observations(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof, intern_user
):
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Normal")
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Watch")
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Alert")
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Watch")

    body = admin_client.get("/admin/dashboard/properties").json()
    row = body["rows"][0]

    assert row["total_observations"] == 4
    assert row["normal_count"] == 1
    assert row["watch_count"] == 2
    assert row["alert_count"] == 1
    assert row["voided_count"] == 0
    assert row["last_severity"] == "Watch"  # last submission was a Watch
    assert row["last_submitted_by_name"] == intern_user.name


def test_dashboard_voided_does_not_count_as_live(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    entry = _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Alert")
    admin_client.patch(
        f"/admin/observations/{entry['id']}/void",
        json={"reason": "Wrong call — voiding for the dashboard test."},
    )

    body = admin_client.get("/admin/dashboard/properties").json()
    row = body["rows"][0]
    # The voided entry should not pollute live counts:
    assert row["total_observations"] == 0
    assert row["alert_count"] == 0
    assert row["voided_count"] == 1
    # last_submitted_at is the latest LIVE submission — none here:
    assert row["last_submitted_at"] is None


def test_dashboard_filter_by_stream(
    admin_client, intern_client, db_session, property_block_a, sensor_zone_block_a_roof, admin_user
):
    # Add a Lender-stream owner + property + zone, plus an observation
    from app.models.owner_profile import OwnerProfile
    from app.models.property import Property
    from app.models.sensor_zone import SensorZone
    from app.models.stream import KycStatus, Stream

    lender = OwnerProfile(
        id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        stream=Stream.LENDER,
        legal_name="Test Lender Bank",
        kyc_status=KycStatus.VERIFIED,
    )
    db_session.add(lender)
    db_session.commit()
    lender_prop = Property(
        id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        name="Lender Building",
        address="X",
        primary_owner_id=lender.id,
        created_by=admin_user.id,
    )
    db_session.add(lender_prop)
    db_session.commit()
    lender_zone = SensorZone(
        id=uuid.UUID("f1111111-1111-1111-1111-111111111111"),
        property_id=lender_prop.id,
        building_label="Tower",
        zone_label="Vault",
    )
    db_session.add(lender_zone)
    db_session.commit()

    # Without filter: both zones appear
    body = admin_client.get("/admin/dashboard/properties").json()
    assert body["total_zones"] == 2

    # Filter by REIT
    body = admin_client.get("/admin/dashboard/properties?stream=reit").json()
    assert body["total_zones"] == 1
    assert body["rows"][0]["stream"] == "reit"

    # Filter by Lender
    body = admin_client.get("/admin/dashboard/properties?stream=lender").json()
    assert body["total_zones"] == 1
    assert body["rows"][0]["stream"] == "lender"
    assert body["rows"][0]["owner_name"] == "Test Lender Bank"

    # Multi-stream filter
    body = admin_client.get(
        "/admin/dashboard/properties?stream=reit&stream=lender"
    ).json()
    assert body["total_zones"] == 2


def test_dashboard_filter_by_severity_includes_only_zones_with_match(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    # Submit only Normal observations
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Normal")

    # Filter by Alert: zone should be excluded (no alerts)
    body = admin_client.get("/admin/dashboard/properties?severity=Alert").json()
    assert body["total_zones"] == 0

    # Filter by Normal: zone included
    body = admin_client.get("/admin/dashboard/properties?severity=Normal").json()
    assert body["total_zones"] == 1


def test_dashboard_search(
    admin_client, property_block_a, sensor_zone_block_a_roof
):
    body = admin_client.get(
        f"/admin/dashboard/properties?search={property_block_a.name[:5]}"
    ).json()
    assert body["total_zones"] == 1

    body = admin_client.get(
        "/admin/dashboard/properties?search=DefinitelyNotAMatch"
    ).json()
    assert body["total_zones"] == 0


def test_dashboard_all_flag_bypasses_filters(
    admin_client, property_block_a, sensor_zone_block_a_roof
):
    # Even with a search that wouldn't match, all=true returns everything
    body = admin_client.get(
        "/admin/dashboard/properties?search=xxxxxx&all=true"
    ).json()
    assert body["total_zones"] >= 1


def test_dashboard_unfiltered_totals_independent_of_filter(
    admin_client, property_block_a, sensor_zone_block_a_roof
):
    body = admin_client.get(
        "/admin/dashboard/properties?search=xxxxxxxxxx"
    ).json()
    # Filter excludes the zone but unfiltered totals still report it
    assert body["total_zones"] == 0
    assert body["total_zones_unfiltered"] == 1
    assert body["total_properties_unfiltered"] == 1
