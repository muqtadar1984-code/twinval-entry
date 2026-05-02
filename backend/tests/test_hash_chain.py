"""
Hash chain unit tests.

These tests are the audit anchor for the system. If they pass, the chain
logic is provably correct against the patent specification: every entry's
hash is a deterministic function of its canonical payload + the previous
entry's hash, any tampering is detectable by walking the chain, and
post-hoc renames of upstream rows (property, owner) cannot retroactively
alter the chain because the entry stores frozen snapshots.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

import pytest

from app.models.observation import ObservationType, Severity
from app.services import hash_chain
from app.services.hash_chain import (
    NewEntryInput,
    build_entry_ref_id,
    canonical_payload,
    compute_hash,
    genesis_prev_hash,
    insert_observation_atomic,
    iso_utc,
    verify_chain,
    verify_entry,
)


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


# Pinned audit anchor — if this hex changes, the genesis seed has been altered
# and the full chain must be re-verified.
EXPECTED_GENESIS_HASH = "5f0255e4b9627ccf79f293d3f55daacc6ef7a493faa7ecdba98eb7507d245e08"


class TestGenesis:
    def test_genesis_hash_is_pinned_constant(self):
        assert genesis_prev_hash() == EXPECTED_GENESIS_HASH

    def test_genesis_hash_matches_sha256_of_seed(self):
        expected = hashlib.sha256(b"TWINVAL_GENESIS_IIUM_PILOT").hexdigest()
        assert genesis_prev_hash() == expected

    def test_genesis_hash_is_64_hex_chars(self):
        h = genesis_prev_hash()
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


def _sample_canonical_kwargs():
    return dict(
        entry_ref_id="TVL-20260501-0001",
        intern_id="11111111-1111-1111-1111-111111111111",
        submitted_at="2026-05-01T10:00:00Z",
        property_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        property_name="IIUM Block A",
        sensor_zone_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        building_label="Block A",
        zone_label="Roof - HVAC",
        owner_profile_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        owner_profile_name="Test REIT Trust",
        stream="reit",
        observation_type="Anomaly",
        description="Visible crack near support beam.",
        severity="Watch",
        photo_url="https://photos.twinval.com/abc.jpg",
        prev_hash=genesis_prev_hash(),
    )


class TestCanonicalPayload:
    def test_canonical_payload_is_deterministic(self):
        kwargs = _sample_canonical_kwargs()
        a = canonical_payload(**kwargs)
        b = canonical_payload(**kwargs)
        assert a == b

    def test_canonical_payload_keys_are_sorted(self):
        s = canonical_payload(**_sample_canonical_kwargs())
        parsed = json.loads(s)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_canonical_payload_has_no_syntactic_whitespace(self):
        # Spaces inside string values are fine; what must not exist is JSON
        # syntactic whitespace between keys/colons/commas, since those bytes
        # would silently change the hash.
        s = canonical_payload(**_sample_canonical_kwargs())
        assert ", " not in s
        assert ": " not in s
        assert "\n" not in s
        assert "\t" not in s

    def test_canonical_payload_treats_missing_photo_as_null(self):
        kwargs = _sample_canonical_kwargs()
        kwargs["photo_url"] = None
        s = canonical_payload(**kwargs)
        assert '"photo_url":null' in s

    def test_canonical_payload_treats_empty_photo_as_null(self):
        # Empty string and None must hash identically so the chain cannot
        # diverge on submission-time formatting differences.
        a = canonical_payload(**{**_sample_canonical_kwargs(), "photo_url": ""})
        b = canonical_payload(**{**_sample_canonical_kwargs(), "photo_url": None})
        assert a == b

    def test_canonical_payload_includes_all_chain_fields(self):
        s = canonical_payload(**_sample_canonical_kwargs())
        parsed = json.loads(s)
        assert set(parsed.keys()) == {
            "building_label",
            "description",
            "entry_ref_id",
            "intern_id",
            "observation_type",
            "owner_profile_id",
            "owner_profile_name",
            "photo_url",
            "prev_hash",
            "property_id",
            "property_name",
            "sensor_zone_id",
            "severity",
            "stream",
            "submitted_at",
            "zone_label",
        }

    @pytest.mark.parametrize(
        "field, mutated",
        [
            ("entry_ref_id", "TVL-20260501-9999"),
            ("intern_id", "99999999-9999-9999-9999-999999999999"),
            ("submitted_at", "2026-05-01T10:00:01Z"),
            ("property_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
            ("property_name", "IIUM Block B"),
            ("sensor_zone_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
            ("building_label", "Block B"),
            ("zone_label", "Roof - Different Zone"),
            ("owner_profile_id", "ffffffff-ffff-ffff-ffff-ffffffffffff"),
            ("owner_profile_name", "Different REIT"),
            ("stream", "lender"),
            ("observation_type", "Maintenance Event"),
            ("description", "Visible crack near support beam!"),
            ("severity", "Alert"),
            ("photo_url", "https://photos.twinval.com/xyz.jpg"),
            ("prev_hash", "0" * 64),
        ],
    )
    def test_any_field_mutation_changes_the_hash(self, field, mutated):
        original = compute_hash(canonical_payload(**_sample_canonical_kwargs()))
        tampered_kwargs = {**_sample_canonical_kwargs(), field: mutated}
        tampered = compute_hash(canonical_payload(**tampered_kwargs))
        assert original != tampered, f"mutating {field} did not change the hash"


class TestEntryRefId:
    def test_format(self):
        dt = datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert build_entry_ref_id(dt, 42) == "TVL-20260501-0042"

    def test_zero_pads_counter_to_four_digits(self):
        dt = datetime(2026, 1, 9, tzinfo=timezone.utc)
        assert build_entry_ref_id(dt, 1) == "TVL-20260109-0001"
        assert build_entry_ref_id(dt, 9999) == "TVL-20260109-9999"

    def test_normalises_to_utc(self):
        from datetime import timedelta, timezone as tz

        dt_utc8 = datetime(2026, 5, 2, 2, 30, tzinfo=tz(timedelta(hours=8)))
        # 02:30 UTC+8 == 18:30 UTC on the previous day.
        assert build_entry_ref_id(dt_utc8, 1) == "TVL-20260501-0001"


class TestIsoUtc:
    def test_aware_datetime_is_normalised_to_utc(self):
        from datetime import timedelta, timezone as tz

        dt = datetime(2026, 5, 1, 18, 0, 0, tzinfo=tz(timedelta(hours=8)))
        assert iso_utc(dt) == "2026-05-01T10:00:00Z"

    def test_naive_datetime_is_treated_as_utc(self):
        dt = datetime(2026, 5, 1, 10, 0, 0)
        assert iso_utc(dt) == "2026-05-01T10:00:00Z"


# ---------------------------------------------------------------------------
# DB-backed chain tests
# ---------------------------------------------------------------------------


def _make_input(chain_context, severity=Severity.NORMAL, description="ok"):
    return NewEntryInput(
        intern_id=chain_context["intern"].id,
        property_id=chain_context["property"].id,
        sensor_zone_id=chain_context["zone"].id,
        observation_type=ObservationType.VISUAL_INSPECTION,
        description=description,
        severity=severity,
        photo_url=None,
    )


class TestChainInsertion:
    def test_first_entry_links_to_genesis(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        assert entry.chain_sequence == 0
        assert entry.prev_hash == genesis_prev_hash()
        assert entry.entry_ref_id == "TVL-20260501-0001"
        assert len(entry.entry_hash) == 64

    def test_first_entry_captures_snapshots(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        assert entry.property_name == chain_context["property"].name
        assert entry.building_label == chain_context["zone"].building_label
        assert entry.zone_label == chain_context["zone"].zone_label
        assert entry.owner_profile_name == chain_context["owner"].legal_name
        assert entry.stream == chain_context["owner"].stream
        assert entry.owner_profile_id == chain_context["owner"].id

    def test_second_entry_links_to_first(self, db_session, chain_context):
        first = insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="first"),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()
        second = insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="second"),
            submitted_at=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        assert second.chain_sequence == 1
        assert second.prev_hash == first.entry_hash
        assert second.entry_ref_id == "TVL-20260501-0002"
        assert second.entry_hash != first.entry_hash

    def test_daily_counter_resets_per_utc_day(self, db_session, chain_context):
        insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="day-1-a"),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="day-1-b"),
            submitted_at=datetime(2026, 5, 1, 22, 0, tzinfo=timezone.utc),
        )
        day2 = insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="day-2"),
            submitted_at=datetime(2026, 5, 2, 1, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        assert day2.entry_ref_id == "TVL-20260502-0001"
        assert day2.chain_sequence == 2  # global sequence keeps incrementing


class TestSnapshotIntegrity:
    """
    The snapshot fields are what make the chain self-contained: even if a
    property or owner row is later renamed or archived, the chain entry
    still verifies and the audit log remains human-readable.
    """

    def test_renaming_property_does_not_break_existing_entry(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()
        original_hash = entry.entry_hash
        original_name_snapshot = entry.property_name

        # Rename the property after the fact (e.g., admin updates display name).
        chain_context["property"].name = "IIUM Block A — Renamed"
        db_session.commit()
        db_session.refresh(entry)

        # The chain entry's snapshot is frozen; verification still passes.
        assert entry.property_name == original_name_snapshot
        assert entry.property_name != chain_context["property"].name
        result = verify_entry(db_session, entry)
        assert result.valid is True
        assert result.computed_hash == original_hash

    def test_renaming_owner_does_not_break_existing_entry(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        chain_context["owner"].legal_name = "Test REIT Trust (Successor)"
        db_session.commit()
        db_session.refresh(entry)

        assert entry.owner_profile_name == "Test REIT Trust"
        result = verify_entry(db_session, entry)
        assert result.valid is True


class TestReferenceValidation:
    def test_missing_property_raises(self, db_session, chain_context):
        bad = NewEntryInput(
            intern_id=chain_context["intern"].id,
            property_id=uuid.uuid4(),
            sensor_zone_id=chain_context["zone"].id,
            observation_type=ObservationType.VISUAL_INSPECTION,
            description="x",
            severity=Severity.NORMAL,
            photo_url=None,
        )
        with pytest.raises(ValueError, match="Property"):
            insert_observation_atomic(db_session, bad)

    def test_zone_not_belonging_to_property_raises(
        self, db_session, chain_context, property_block_a, owner_profile_reit, admin_user
    ):
        from app.models.property import Property
        from app.models.sensor_zone import SensorZone

        other_property = Property(
            id=uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            name="Other Property",
            address="Elsewhere",
            primary_owner_id=owner_profile_reit.id,
            created_by=admin_user.id,
        )
        other_zone = SensorZone(
            id=uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            property_id=other_property.id,
            building_label="X",
            zone_label="Y",
        )
        db_session.add_all([other_property, other_zone])
        db_session.commit()

        bad = NewEntryInput(
            intern_id=chain_context["intern"].id,
            property_id=property_block_a.id,
            sensor_zone_id=other_zone.id,  # belongs to a different property
            observation_type=ObservationType.VISUAL_INSPECTION,
            description="x",
            severity=Severity.NORMAL,
            photo_url=None,
        )
        with pytest.raises(ValueError, match="does not belong"):
            insert_observation_atomic(db_session, bad)


class TestChainVerification:
    def test_intact_entry_verifies(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        result = verify_entry(db_session, entry)
        assert result.valid is True
        assert result.chain_intact is True
        assert result.computed_hash == result.stored_hash

    def test_payload_tamper_detected(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="original"),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        entry.description = "tampered"
        db_session.commit()

        result = verify_entry(db_session, entry)
        assert result.valid is False
        assert result.computed_hash != result.stored_hash

    def test_snapshot_field_tamper_detected(self, db_session, chain_context):
        entry = insert_observation_atomic(
            db_session,
            _make_input(chain_context),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        # Tampering with the snapshot itself (not the upstream row) breaks the hash.
        entry.property_name = "Spoofed Property"
        db_session.commit()

        result = verify_entry(db_session, entry)
        assert result.valid is False

    def test_prev_hash_tamper_detected(self, db_session, chain_context):
        first = insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="first"),
            submitted_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
        )
        db_session.commit()
        second = insert_observation_atomic(
            db_session,
            _make_input(chain_context, description="second"),
            submitted_at=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
        )
        db_session.commit()

        second.prev_hash = "0" * 64
        db_session.commit()

        result = verify_entry(db_session, second)
        assert result.chain_intact is False

    def test_full_chain_audit_clean(self, db_session, chain_context):
        for i in range(5):
            insert_observation_atomic(
                db_session,
                _make_input(chain_context, description=f"entry-{i}"),
                submitted_at=datetime(2026, 5, 1, 10 + i, 0, tzinfo=timezone.utc),
            )
        db_session.commit()

        audit = verify_chain(db_session)
        assert audit.total_entries == 5
        assert audit.broken_links == []
        assert audit.chain_valid is True

    def test_full_chain_audit_flags_tampered_entry(self, db_session, chain_context):
        entries = []
        for i in range(3):
            entries.append(
                insert_observation_atomic(
                    db_session,
                    _make_input(chain_context, description=f"entry-{i}"),
                    submitted_at=datetime(2026, 5, 1, 10 + i, 0, tzinfo=timezone.utc),
                )
            )
        db_session.commit()

        entries[1].description = "tampered after the fact"
        db_session.commit()

        audit = verify_chain(db_session)
        assert entries[1].entry_ref_id in audit.broken_links
        assert audit.chain_valid is False

    def test_full_chain_audit_flags_broken_linkage(self, db_session, chain_context):
        entries = []
        for i in range(3):
            entries.append(
                insert_observation_atomic(
                    db_session,
                    _make_input(chain_context, description=f"entry-{i}"),
                    submitted_at=datetime(2026, 5, 1, 10 + i, 0, tzinfo=timezone.utc),
                )
            )
        db_session.commit()

        entries[1].entry_hash = "f" * 64
        db_session.commit()

        audit = verify_chain(db_session)
        assert audit.chain_valid is False
        assert entries[1].entry_ref_id in audit.broken_links
        assert entries[2].entry_ref_id in audit.broken_links


class TestUuidIsStringInPayload:
    """
    Regression guard: UUIDs must be serialised as strings in the canonical
    payload. If a uuid.UUID object is ever passed in directly, json.dumps
    will raise — better to crash than silently double-hash.
    """

    def test_uuid_must_be_string(self):
        with pytest.raises(TypeError):
            canonical_payload(
                **{
                    **_sample_canonical_kwargs(),
                    "intern_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),  # type: ignore[arg-type]
                }
            )
