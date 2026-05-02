"""
TwinVal hash chain service.

Each observation entry is a tamper-evident record:

    entry_hash = SHA256(canonical_payload(entry || prev_hash))

The chain is bootstrapped with a genesis prev_hash:

    genesis_prev_hash = SHA256(GENESIS_SEED)

Inserts are atomic under a row-level lock on the most recent chain entry,
so concurrent submissions cannot fork the chain.

Canonical payload (sorted keys, no whitespace):

    {
      "building_label":           snapshot of zone.building_label,
      "description":              the intern's text,
      "entry_ref_id":             "TVL-YYYYMMDD-NNNN",
      "intern_id":                user UUID,
      "observation_type":         enum value,
      "owner_profile_id":         primary owner UUID at submission time,
      "owner_profile_name":       snapshot of owner.legal_name,
      "photo_url":                URL or null,
      "prev_hash":                hash of preceding entry (or genesis),
      "property_id":              property UUID,
      "property_name":            snapshot of property.name,
      "sensor_zone_id":           zone UUID,
      "severity":                 enum value,
      "stream":                   snapshot of owner.stream value,
      "submitted_at":             ISO-8601 UTC,
      "zone_label":               snapshot of zone.zone_label
    }

The FKs let the chain be replayed against current data. The snapshot
fields keep the audit log self-explanatory even if upstream rows are
later renamed or archived.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.observation import ObservationEntry, ObservationType, Severity
from app.models.owner_profile import OwnerProfile
from app.models.property import Property
from app.models.sensor_zone import SensorZone
from app.models.stream import Stream


def genesis_prev_hash(seed: Optional[str] = None) -> str:
    """SHA-256 of the genesis seed. Anchors the chain at sequence 0."""
    if seed is None:
        seed = get_settings().genesis_seed
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def canonical_payload(
    *,
    entry_ref_id: str,
    intern_id: str,
    submitted_at: str,
    property_id: str,
    property_name: str,
    sensor_zone_id: str,
    building_label: str,
    zone_label: str,
    owner_profile_id: str,
    owner_profile_name: str,
    stream: str,
    observation_type: str,
    description: str,
    severity: str,
    photo_url: Optional[str],
    prev_hash: str,
) -> str:
    """
    Serialize the entry to a canonical JSON string for hashing.

    - Keys are emitted in sorted order (json.dumps sort_keys=True).
    - No whitespace between separators.
    - UTF-8.
    - photo_url is null when absent (never the empty string).
    - All inputs must already be in their final wire form (UUIDs as strings,
      submitted_at as an ISO-8601 UTC string, enums as their .value).
    """
    payload = {
        "building_label": building_label,
        "description": description,
        "entry_ref_id": entry_ref_id,
        "intern_id": intern_id,
        "observation_type": observation_type,
        "owner_profile_id": owner_profile_id,
        "owner_profile_name": owner_profile_name,
        "photo_url": photo_url if photo_url else None,
        "prev_hash": prev_hash,
        "property_id": property_id,
        "property_name": property_name,
        "sensor_zone_id": sensor_zone_id,
        "severity": severity,
        "stream": stream,
        "submitted_at": submitted_at,
        "zone_label": zone_label,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(canonical_str: str) -> str:
    """SHA-256 hex digest of the canonical payload."""
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def iso_utc(dt: datetime) -> str:
    """Render a datetime as ISO-8601 in UTC with a trailing Z, second precision."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_entry_ref_id(submitted_at_utc: datetime, daily_counter: int) -> str:
    """Format: TVL-YYYYMMDD-NNNN where NNNN is the within-day counter, 1-indexed."""
    if submitted_at_utc.tzinfo is None:
        submitted_at_utc = submitted_at_utc.replace(tzinfo=timezone.utc)
    else:
        submitted_at_utc = submitted_at_utc.astimezone(timezone.utc)
    date_part = submitted_at_utc.strftime("%Y%m%d")
    return f"TVL-{date_part}-{daily_counter:04d}"


@dataclass
class ChainHead:
    prev_hash: str
    next_sequence: int


def _read_chain_head(db: Session, *, lock: bool) -> ChainHead:
    """
    Return the prev_hash + next chain_sequence for a new insert.

    When lock=True, takes a row-level FOR UPDATE lock on the latest entry
    (Postgres). On engines without row locking (SQLite in tests) the lock
    is silently skipped — concurrency safety is a Postgres-only guarantee.
    """
    stmt = (
        select(ObservationEntry)
        .order_by(ObservationEntry.chain_sequence.desc())
        .limit(1)
    )
    if lock and db.bind is not None and db.bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    latest = db.execute(stmt).scalar_one_or_none()

    if latest is None:
        return ChainHead(prev_hash=genesis_prev_hash(), next_sequence=0)
    return ChainHead(prev_hash=latest.entry_hash, next_sequence=latest.chain_sequence + 1)


def _next_daily_counter(db: Session, submitted_at_utc: datetime) -> int:
    """Count how many entries exist for the same UTC date and return count+1."""
    day_start = submitted_at_utc.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    day_end = day_start.replace(hour=23, minute=59, second=59, microsecond=999_999)
    count = db.execute(
        select(func.count(ObservationEntry.id)).where(
            ObservationEntry.submitted_at >= day_start,
            ObservationEntry.submitted_at <= day_end,
        )
    ).scalar_one()
    return count + 1


@dataclass
class NewEntryInput:
    """
    Caller-supplied data for a new observation. The service resolves
    Property, SensorZone, and OwnerProfile rows internally to capture the
    canonical snapshot fields — callers must not pass snapshot strings
    directly, or chain integrity could be subverted by a buggy caller.
    """

    intern_id: uuid.UUID
    property_id: uuid.UUID
    sensor_zone_id: uuid.UUID
    observation_type: ObservationType
    description: str
    severity: Severity
    photo_url: Optional[str]


@dataclass
class ResolvedSnapshot:
    property: Property
    sensor_zone: SensorZone
    owner_profile: OwnerProfile


def _resolve_snapshot(db: Session, payload: NewEntryInput) -> ResolvedSnapshot:
    """
    Look up the rows referenced by NewEntryInput and validate consistency.
    Raises ValueError if any reference is missing or the sensor zone does
    not belong to the property.
    """
    prop = db.get(Property, payload.property_id)
    if prop is None:
        raise ValueError(f"Property {payload.property_id} not found")

    zone = db.get(SensorZone, payload.sensor_zone_id)
    if zone is None:
        raise ValueError(f"SensorZone {payload.sensor_zone_id} not found")
    if zone.property_id != prop.id:
        raise ValueError(
            f"SensorZone {zone.id} does not belong to property {prop.id}"
        )

    owner = db.get(OwnerProfile, prop.primary_owner_id)
    if owner is None:
        raise ValueError(
            f"OwnerProfile {prop.primary_owner_id} (primary owner of "
            f"property {prop.id}) not found"
        )

    return ResolvedSnapshot(property=prop, sensor_zone=zone, owner_profile=owner)


def insert_observation_atomic(
    db: Session,
    payload: NewEntryInput,
    *,
    submitted_at: Optional[datetime] = None,
) -> ObservationEntry:
    """
    Atomically insert a new chain entry.

    Flow:
      1. Resolve property + zone + owner snapshot rows.
      2. Lock the latest entry row (FOR UPDATE on Postgres).
      3. Determine prev_hash + next chain_sequence.
      4. Compute entry_ref_id from submitted_at and the daily counter.
      5. Compute canonical payload + entry_hash.
      6. Insert and flush within the caller's transaction.

    The caller is expected to manage the outer transaction (commit/rollback).
    """
    submitted_at_utc = (submitted_at or datetime.now(timezone.utc)).astimezone(timezone.utc)

    snap = _resolve_snapshot(db, payload)
    head = _read_chain_head(db, lock=True)
    daily_counter = _next_daily_counter(db, submitted_at_utc)
    entry_ref_id = build_entry_ref_id(submitted_at_utc, daily_counter)

    canonical = canonical_payload(
        entry_ref_id=entry_ref_id,
        intern_id=str(payload.intern_id),
        submitted_at=iso_utc(submitted_at_utc),
        property_id=str(snap.property.id),
        property_name=snap.property.name,
        sensor_zone_id=str(snap.sensor_zone.id),
        building_label=snap.sensor_zone.building_label,
        zone_label=snap.sensor_zone.zone_label,
        owner_profile_id=str(snap.owner_profile.id),
        owner_profile_name=snap.owner_profile.legal_name,
        stream=snap.owner_profile.stream.value,
        observation_type=payload.observation_type.value,
        description=payload.description,
        severity=payload.severity.value,
        photo_url=payload.photo_url,
        prev_hash=head.prev_hash,
    )
    entry_hash = compute_hash(canonical)

    entry = ObservationEntry(
        entry_ref_id=entry_ref_id,
        intern_id=payload.intern_id,
        property_id=snap.property.id,
        sensor_zone_id=snap.sensor_zone.id,
        owner_profile_id=snap.owner_profile.id,
        submitted_at=submitted_at_utc,
        property_name=snap.property.name,
        building_label=snap.sensor_zone.building_label,
        zone_label=snap.sensor_zone.zone_label,
        owner_profile_name=snap.owner_profile.legal_name,
        stream=snap.owner_profile.stream,
        observation_type=payload.observation_type,
        description=payload.description,
        severity=payload.severity,
        photo_url=payload.photo_url,
        entry_hash=entry_hash,
        prev_hash=head.prev_hash,
        chain_sequence=head.next_sequence,
    )
    db.add(entry)
    db.flush()
    return entry


@dataclass
class VerificationResult:
    valid: bool
    computed_hash: str
    stored_hash: str
    chain_intact: bool


def _canonical_for_entry(entry: ObservationEntry) -> str:
    """Reproduce the canonical payload for an existing entry row."""
    return canonical_payload(
        entry_ref_id=entry.entry_ref_id,
        intern_id=str(entry.intern_id),
        submitted_at=iso_utc(entry.submitted_at),
        property_id=str(entry.property_id),
        property_name=entry.property_name,
        sensor_zone_id=str(entry.sensor_zone_id),
        building_label=entry.building_label,
        zone_label=entry.zone_label,
        owner_profile_id=str(entry.owner_profile_id),
        owner_profile_name=entry.owner_profile_name,
        stream=entry.stream.value,
        observation_type=entry.observation_type.value,
        description=entry.description,
        severity=entry.severity.value,
        photo_url=entry.photo_url,
        prev_hash=entry.prev_hash,
    )


def verify_entry(db: Session, entry: ObservationEntry) -> VerificationResult:
    """
    Recompute the entry's canonical hash and compare to stored entry_hash.
    Also check that prev_hash matches the previous entry in the chain
    (or the genesis hash for sequence 0).
    """
    computed = compute_hash(_canonical_for_entry(entry))

    if entry.chain_sequence == 0:
        chain_intact = entry.prev_hash == genesis_prev_hash()
    else:
        prev = db.execute(
            select(ObservationEntry).where(
                ObservationEntry.chain_sequence == entry.chain_sequence - 1
            )
        ).scalar_one_or_none()
        chain_intact = prev is not None and prev.entry_hash == entry.prev_hash

    return VerificationResult(
        valid=(computed == entry.entry_hash),
        computed_hash=computed,
        stored_hash=entry.entry_hash,
        chain_intact=chain_intact,
    )


@dataclass
class ChainAuditResult:
    total_entries: int
    broken_links: list[str]
    chain_valid: bool


def verify_chain(db: Session) -> ChainAuditResult:
    """
    Walk every entry in chain_sequence order. For each entry, recompute its
    hash and check linkage to the previous entry. Returns the list of
    entry_ref_ids whose hash or linkage is broken.
    """
    entries = (
        db.execute(
            select(ObservationEntry).order_by(ObservationEntry.chain_sequence.asc())
        )
        .scalars()
        .all()
    )

    broken: list[str] = []
    expected_prev = genesis_prev_hash()
    expected_seq = 0

    for entry in entries:
        if entry.chain_sequence != expected_seq or entry.prev_hash != expected_prev:
            broken.append(entry.entry_ref_id)
            expected_prev = entry.entry_hash
            expected_seq = entry.chain_sequence + 1
            continue

        if compute_hash(_canonical_for_entry(entry)) != entry.entry_hash:
            broken.append(entry.entry_ref_id)

        expected_prev = entry.entry_hash
        expected_seq = entry.chain_sequence + 1

    return ChainAuditResult(
        total_entries=len(entries),
        broken_links=broken,
        chain_valid=len(broken) == 0,
    )
