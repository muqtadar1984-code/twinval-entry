"""Activity dashboard endpoint."""

from datetime import datetime, timedelta, timezone

from app.models.observation import ObservationType, Severity
from app.services.hash_chain import NewEntryInput, insert_observation_atomic


def _submit_observation(intern_client, property_id, zone_id, severity="Normal"):
    r = intern_client.post(
        "/observations",
        data={
            "property_id": str(property_id),
            "sensor_zone_id": str(zone_id),
            "observation_type": "Anomaly",
            "description": f"A {severity} entry for the activity test fixtures.",
            "severity": severity,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _backdated_entry(db_session, intern_user, property_id, zone_id, *, severity, days_ago):
    """Insert an observation with a manually-set submitted_at (for stale-zone / trend tests)."""
    submitted = datetime.now(timezone.utc) - timedelta(days=days_ago)
    entry = insert_observation_atomic(
        db_session,
        NewEntryInput(
            intern_id=intern_user.id,
            property_id=property_id,
            sensor_zone_id=zone_id,
            observation_type=ObservationType.VISUAL_INSPECTION,
            description=f"Backdated {severity} entry, {days_ago} days ago — fixture only.",
            severity=Severity(severity),
            photo_url=None,
        ),
        submitted_at=submitted,
    )
    db_session.commit()
    return entry


def test_activity_admin_only(intern_client):
    r = intern_client.get("/admin/dashboard/activity")
    assert r.status_code == 403


def test_activity_empty_state(admin_client):
    r = admin_client.get("/admin/dashboard/activity")
    assert r.status_code == 200
    body = r.json()
    assert body["pending_review"] == []
    assert body["pending_review_total"] == 0
    assert body["stale_zones"] == []
    assert body["stale_zones_total"] == 0
    assert body["submissions_last_7_days"] == 0
    assert len(body["weekly_buckets"]) == 12
    for b in body["weekly_buckets"]:
        assert b["total"] == 0


def test_activity_pending_review_only_unreviewed_watch_and_alerts(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    # Submit one Normal, one Watch, one Alert
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Normal")
    watch = _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Watch")
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Alert")

    body = admin_client.get("/admin/dashboard/activity").json()
    # Only Watch + Alert, both unreviewed
    assert body["pending_review_total"] == 2
    severities = sorted([item["severity"] for item in body["pending_review"]])
    assert severities == ["Alert", "Watch"]

    # After reviewing the Watch, only Alert remains
    admin_client.patch(
        f"/admin/observations/{watch['id']}/review",
        json={"reviewer_note": "looked at it"},
    )
    body = admin_client.get("/admin/dashboard/activity").json()
    assert body["pending_review_total"] == 1
    assert body["pending_review"][0]["severity"] == "Alert"


def test_activity_pending_review_excludes_voided(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    alert = _submit_observation(
        intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Alert"
    )
    # Void the alert
    admin_client.patch(
        f"/admin/observations/{alert['id']}/void",
        json={"reason": "voiding for the activity-test fixture coverage"},
    )
    body = admin_client.get("/admin/dashboard/activity").json()
    assert body["pending_review_total"] == 0


def test_activity_stale_zones_includes_never_observed(
    admin_client, property_block_a, sensor_zone_block_a_roof
):
    body = admin_client.get("/admin/dashboard/activity").json()
    assert body["stale_zones_total"] == 1
    z = body["stale_zones"][0]
    assert z["zone_id"] == str(sensor_zone_block_a_roof.id)
    assert z["never_observed"] is True
    assert z["last_submitted_at"] is None
    assert z["days_stale"] is None


def test_activity_stale_zones_excludes_recently_observed(
    admin_client, intern_client, property_block_a, sensor_zone_block_a_roof
):
    _submit_observation(intern_client, property_block_a.id, sensor_zone_block_a_roof.id, "Normal")
    body = admin_client.get("/admin/dashboard/activity").json()
    # Just-submitted zone is fresh, not stale.
    assert body["stale_zones_total"] == 0


def test_activity_stale_zones_threshold_param(
    admin_client, db_session, intern_user, property_block_a, sensor_zone_block_a_roof
):
    _backdated_entry(
        db_session,
        intern_user,
        property_block_a.id,
        sensor_zone_block_a_roof.id,
        severity="Normal",
        days_ago=10,
    )
    # Default threshold (14): 10-day-old observation is fresh
    body = admin_client.get("/admin/dashboard/activity").json()
    assert body["stale_zones_total"] == 0

    # Tighter threshold (5): 10-day-old observation is stale
    body = admin_client.get("/admin/dashboard/activity?stale_threshold_days=5").json()
    assert body["stale_zones_total"] == 1
    z = body["stale_zones"][0]
    assert z["never_observed"] is False
    assert z["days_stale"] >= 9


def test_activity_weekly_buckets_count_correctly(
    admin_client, db_session, intern_user, property_block_a, sensor_zone_block_a_roof
):
    # 3 entries this week, 1 last week, 1 way old (outside window)
    for _ in range(3):
        _backdated_entry(
            db_session, intern_user, property_block_a.id, sensor_zone_block_a_roof.id,
            severity="Normal", days_ago=1,
        )
    _backdated_entry(
        db_session, intern_user, property_block_a.id, sensor_zone_block_a_roof.id,
        severity="Watch", days_ago=8,
    )
    _backdated_entry(
        db_session, intern_user, property_block_a.id, sensor_zone_block_a_roof.id,
        severity="Alert", days_ago=200,
    )

    body = admin_client.get("/admin/dashboard/activity").json()
    buckets = body["weekly_buckets"]
    assert len(buckets) == 12
    total_in_window = sum(b["total"] for b in buckets)
    # The 200-day-old entry is out of the 12-week window
    assert total_in_window == 4

    # Most recent bucket (last in list) should have 3 Normals
    last = buckets[-1]
    assert last["normal"] == 3
    assert last["total"] == 3


def test_activity_photo_coverage(
    admin_client, db_session, intern_user, property_block_a, sensor_zone_block_a_roof
):
    # 2 alerts: one with photo, one without
    insert_observation_atomic(
        db_session,
        NewEntryInput(
            intern_id=intern_user.id,
            property_id=property_block_a.id,
            sensor_zone_id=sensor_zone_block_a_roof.id,
            observation_type=ObservationType.ANOMALY,
            description="Alert with photo attached for the coverage test.",
            severity=Severity.ALERT,
            photo_url="https://photos.example/abc.jpg",
        ),
    )
    insert_observation_atomic(
        db_session,
        NewEntryInput(
            intern_id=intern_user.id,
            property_id=property_block_a.id,
            sensor_zone_id=sensor_zone_block_a_roof.id,
            observation_type=ObservationType.ANOMALY,
            description="Alert WITHOUT photo, for the coverage gap test.",
            severity=Severity.ALERT,
            photo_url=None,
        ),
    )
    db_session.commit()

    body = admin_client.get("/admin/dashboard/activity").json()
    pc = body["photo_coverage"]
    assert pc["total_alerts"] == 2
    assert pc["alerts_with_photo"] == 1
    assert pc["alert_coverage_pct"] == 50.0


def test_activity_submissions_last_7_days(
    admin_client, db_session, intern_user, property_block_a, sensor_zone_block_a_roof
):
    _backdated_entry(db_session, intern_user, property_block_a.id, sensor_zone_block_a_roof.id, severity="Normal", days_ago=1)
    _backdated_entry(db_session, intern_user, property_block_a.id, sensor_zone_block_a_roof.id, severity="Normal", days_ago=3)
    _backdated_entry(db_session, intern_user, property_block_a.id, sensor_zone_block_a_roof.id, severity="Normal", days_ago=10)

    body = admin_client.get("/admin/dashboard/activity").json()
    assert body["submissions_last_7_days"] == 2
