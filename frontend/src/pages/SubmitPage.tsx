import { AlertCircle, CheckCircle2, ImagePlus, Loader2, Plus, Trash2, X } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EntryRefId } from "../components/EntryRefId";
import { HashDisplay } from "../components/HashDisplay";
import { InlineSpinner } from "../components/LoadingState";
import { SeverityBadge } from "../components/SeverityBadge";
import {
  observations as obsApi,
  ownerProfiles as ownerApi,
  properties as propApi,
  sensorZones as zoneApi,
} from "../lib/api";
import { formatBytes } from "../lib/format";
import type {
  Observation,
  ObservationType,
  OwnerProfile,
  Property,
  SensorZone,
  Severity,
  Stream,
} from "../types/api";
import { STREAM_LABELS } from "../types/api";

const OBSERVATION_TYPES: ObservationType[] = [
  "Anomaly",
  "Maintenance Event",
  "Visual Inspection",
  "Sensor Health",
];

const SEVERITIES: Severity[] = ["Normal", "Watch", "Alert"];

const STREAMS: Stream[] = [
  "reit",
  "lender",
  "individual",
  "insurer",
  "government",
  "family_office",
  "developer",
];

const MAX_PHOTO_BYTES = 5 * 1024 * 1024;
const ALLOWED_PHOTO_MIME = ["image/jpeg", "image/png", "image/webp", "image/heic"];

export function SubmitPage() {
  // Loaded reference data
  const [properties, setProperties] = useState<Property[]>([]);
  const [zones, setZones] = useState<SensorZone[]>([]);
  const [owners, setOwners] = useState<OwnerProfile[]>([]);
  const [propertiesLoading, setPropertiesLoading] = useState(true);

  // Form state
  const [propertyId, setPropertyId] = useState<string>("");
  const [zoneId, setZoneId] = useState<string>("");
  const [observationType, setObservationType] = useState<ObservationType>("Visual Inspection");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState<Severity>("Normal");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [success, setSuccess] = useState<Observation | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Inline-create flags
  const [showCreateProperty, setShowCreateProperty] = useState(false);
  const [showCreateZone, setShowCreateZone] = useState(false);

  useEffect(() => {
    propApi
      .list({ limit: 200 })
      .then((p) => setProperties(p.items))
      .catch(() => setProperties([]))
      .finally(() => setPropertiesLoading(false));
    ownerApi
      .list({ limit: 200 })
      .then((p) => setOwners(p.items))
      .catch(() => setOwners([]));
  }, []);

  useEffect(() => {
    if (!propertyId) {
      setZones([]);
      setZoneId("");
      return;
    }
    zoneApi
      .list(propertyId, { limit: 200 })
      .then((p) => setZones(p.items))
      .catch(() => setZones([]));
    setZoneId("");
  }, [propertyId]);

  useEffect(() => {
    if (!photo) {
      setPhotoPreview(null);
      return;
    }
    const url = URL.createObjectURL(photo);
    setPhotoPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const descLen = description.trim().length;
  const isValid = useMemo(() => {
    return propertyId && zoneId && descLen >= 20 && descLen <= 1000;
  }, [propertyId, zoneId, descLen]);

  function onSelectPhoto(file: File | null) {
    setFieldErrors((p) => ({ ...p, photo: "" }));
    if (!file) {
      setPhoto(null);
      return;
    }
    if (!ALLOWED_PHOTO_MIME.includes(file.type)) {
      setFieldErrors((p) => ({
        ...p,
        photo: `Unsupported format. Allowed: JPEG, PNG, WEBP, HEIC.`,
      }));
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      setFieldErrors((p) => ({
        ...p,
        photo: `Photo is too large (${formatBytes(file.size)}). Max ${formatBytes(MAX_PHOTO_BYTES)}.`,
      }));
      return;
    }
    setPhoto(file);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    const errs: Record<string, string> = {};
    if (!propertyId) errs.property = "Select a property.";
    if (!zoneId) errs.zone = "Select a sensor zone.";
    if (descLen < 20) errs.description = `Description must be at least 20 characters (currently ${descLen}).`;
    if (descLen > 1000) errs.description = `Description must be at most 1000 characters (currently ${descLen}).`;
    setFieldErrors(errs);
    if (Object.values(errs).some(Boolean)) return;

    setSubmitting(true);
    try {
      const result = await obsApi.submit({
        property_id: propertyId,
        sensor_zone_id: zoneId,
        observation_type: observationType,
        description: description.trim(),
        severity,
        photo,
      });
      setSuccess(result);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setSubmitError(typeof detail === "string" ? detail : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setSuccess(null);
    setSubmitError(null);
    setDescription("");
    setSeverity("Normal");
    setObservationType("Visual Inspection");
    setPhoto(null);
    // Keep property + zone — submitting another for same location is the common case
  }

  if (success) {
    return <SuccessPanel observation={success} onAnother={resetForm} />;
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-ink">New Observation</h1>
      <p className="mt-1 text-sm text-ink-muted">
        All fields are required except the photo. Submission inserts an immutable entry into
        the chain.
      </p>

      <form onSubmit={onSubmit} className="mt-6 space-y-5">
        {/* Property */}
        <div className="card p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <label htmlFor="property" className="label !mb-0">
              Property
            </label>
            <button
              type="button"
              onClick={() => setShowCreateProperty((s) => !s)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              {showCreateProperty ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
              {showCreateProperty ? "Cancel" : "Enrol new"}
            </button>
          </div>

          {showCreateProperty ? (
            <CreatePropertyInline
              owners={owners}
              onCreated={(p) => {
                setProperties((prev) => [p, ...prev]);
                setPropertyId(p.id);
                setShowCreateProperty(false);
              }}
            />
          ) : (
            <select
              id="property"
              className="input mt-2"
              value={propertyId}
              onChange={(e) => setPropertyId(e.target.value)}
              disabled={propertiesLoading || submitting}
            >
              <option value="">{propertiesLoading ? "Loading…" : "Select a property"}</option>
              {properties.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {STREAM_LABELS[p.primary_owner_stream]} · {p.primary_owner_name}
                </option>
              ))}
            </select>
          )}
          {fieldErrors.property && <p className="field-error">{fieldErrors.property}</p>}
        </div>

        {/* Sensor zone */}
        <div className="card p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <label htmlFor="zone" className="label !mb-0">
              Sensor Zone
            </label>
            {propertyId && (
              <button
                type="button"
                onClick={() => setShowCreateZone((s) => !s)}
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
              >
                {showCreateZone ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
                {showCreateZone ? "Cancel" : "Add zone"}
              </button>
            )}
          </div>

          {!propertyId ? (
            <p className="mt-2 text-xs text-ink-muted">Select a property first.</p>
          ) : showCreateZone ? (
            <CreateZoneInline
              propertyId={propertyId}
              onCreated={(z) => {
                setZones((prev) => [...prev, z]);
                setZoneId(z.id);
                setShowCreateZone(false);
              }}
            />
          ) : (
            <select
              id="zone"
              className="input mt-2"
              value={zoneId}
              onChange={(e) => setZoneId(e.target.value)}
              disabled={submitting || zones.length === 0}
            >
              <option value="">{zones.length === 0 ? "No zones — add one" : "Select a zone"}</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.building_label} · {z.zone_label}
                </option>
              ))}
            </select>
          )}
          {fieldErrors.zone && <p className="field-error">{fieldErrors.zone}</p>}
        </div>

        {/* Observation type */}
        <div className="card p-4 sm:p-5">
          <label className="label">Observation Type</label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {OBSERVATION_TYPES.map((t) => {
              const active = observationType === t;
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => setObservationType(t)}
                  className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
                    active
                      ? "border-primary bg-primary-50 text-primary"
                      : "border-border bg-surface text-ink-muted hover:border-primary/40"
                  }`}
                >
                  {t}
                </button>
              );
            })}
          </div>
        </div>

        {/* Description */}
        <div className="card p-4 sm:p-5">
          <label htmlFor="description" className="label">
            Description
          </label>
          <textarea
            id="description"
            rows={4}
            className="input"
            placeholder="What did you observe? Be specific — include location detail, what changed, and any sensor readings if relevant."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={submitting}
          />
          <div className="mt-1 flex items-center justify-between text-xs">
            <span className={fieldErrors.description ? "text-danger" : "text-ink-subtle"}>
              {fieldErrors.description || "Min 20 characters, max 1000."}
            </span>
            <span className={`mono ${descLen > 1000 ? "text-danger" : "text-ink-subtle"}`}>
              {descLen}/1000
            </span>
          </div>
        </div>

        {/* Severity */}
        <div className="card p-4 sm:p-5">
          <label className="label">Severity</label>
          <div className="grid grid-cols-3 gap-2">
            {SEVERITIES.map((s) => {
              const active = severity === s;
              const colorOn =
                s === "Normal"
                  ? "border-accent bg-accent-50 text-accent-700"
                  : s === "Watch"
                  ? "border-warning bg-warning-50 text-warning-700"
                  : "border-danger bg-danger-50 text-danger-700";
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSeverity(s)}
                  className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition ${
                    active ? colorOn : "border-border text-ink-muted hover:border-ink-subtle"
                  }`}
                >
                  {s}
                </button>
              );
            })}
          </div>
        </div>

        {/* Photo */}
        <div className="card p-4 sm:p-5">
          <label className="label">Photo (optional)</label>
          {photo && photoPreview ? (
            <div className="relative">
              <img
                src={photoPreview}
                alt="Selected"
                className="max-h-64 w-full rounded-lg object-cover"
              />
              <button
                type="button"
                onClick={() => setPhoto(null)}
                className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-surface/95 text-ink shadow-card hover:bg-danger-50 hover:text-danger"
                aria-label="Remove photo"
              >
                <Trash2 className="h-4 w-4" />
              </button>
              <div className="mt-2 text-xs text-ink-muted">
                {photo.name} · {formatBytes(photo.size)}
              </div>
            </div>
          ) : (
            <label
              htmlFor="photo"
              className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-canvas py-8 text-center hover:border-primary/40"
            >
              <ImagePlus className="h-8 w-8 text-ink-subtle" />
              <span className="mt-2 text-sm font-medium text-ink">Tap to attach a photo</span>
              <span className="mt-0.5 text-xs text-ink-muted">
                JPEG, PNG, WEBP, HEIC · max {formatBytes(MAX_PHOTO_BYTES)}
              </span>
              <input
                id="photo"
                type="file"
                accept={ALLOWED_PHOTO_MIME.join(",")}
                className="hidden"
                onChange={(e) => onSelectPhoto(e.target.files?.[0] || null)}
                disabled={submitting}
              />
            </label>
          )}
          {fieldErrors.photo && <p className="field-error">{fieldErrors.photo}</p>}
        </div>

        {submitError && (
          <div className="flex items-start gap-2 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
          <Link to="/dashboard" className="btn-secondary order-2 sm:order-1">
            Cancel
          </Link>
          <button
            type="submit"
            className="btn-primary order-1 sm:order-2"
            disabled={!isValid || submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Submitting…
              </>
            ) : (
              "Submit observation"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline create panels
// ---------------------------------------------------------------------------

function CreatePropertyInline({
  owners,
  onCreated,
}: {
  owners: OwnerProfile[];
  onCreated: (p: Property) => void;
}) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("Malaysia");
  const [primaryOwnerId, setPrimaryOwnerId] = useState("");
  const [showCreateOwner, setShowCreateOwner] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valid = name.length >= 2 && address.length >= 2 && primaryOwnerId;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const p = await propApi.create({
        name,
        address,
        city: city || undefined,
        country: country || undefined,
        primary_owner_id: primaryOwnerId,
      });
      onCreated(p);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not create property.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-border bg-canvas p-4">
      <div>
        <label className="label">Owner</label>
        {showCreateOwner ? (
          <CreateOwnerInline
            onCreated={(o) => {
              setPrimaryOwnerId(o.id);
              setShowCreateOwner(false);
            }}
            onCancel={() => setShowCreateOwner(false)}
          />
        ) : (
          <div className="flex gap-2">
            <select
              className="input"
              value={primaryOwnerId}
              onChange={(e) => setPrimaryOwnerId(e.target.value)}
            >
              <option value="">Select an owner</option>
              {owners.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.legal_name} ({STREAM_LABELS[o.stream]})
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setShowCreateOwner(true)}
              className="btn-secondary"
            >
              <Plus className="h-3.5 w-3.5" /> New
            </button>
          </div>
        )}
      </div>
      <div>
        <label className="label">Property name</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div>
        <label className="label">Address</label>
        <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">City</label>
          <input className="input" value={city} onChange={(e) => setCity(e.target.value)} />
        </div>
        <div>
          <label className="label">Country</label>
          <input className="input" value={country} onChange={(e) => setCountry(e.target.value)} />
        </div>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <button
        type="button"
        onClick={submit}
        disabled={!valid || busy}
        className="btn-primary w-full"
      >
        {busy ? <InlineSpinner /> : "Create property"}
      </button>
    </div>
  );
}

function CreateOwnerInline({
  onCreated,
  onCancel,
}: {
  onCreated: (o: OwnerProfile) => void;
  onCancel: () => void;
}) {
  const [stream, setStream] = useState<Stream>("individual");
  const [legalName, setLegalName] = useState("");
  const [legalId, setLegalId] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const o = await ownerApi.create({
        stream,
        legal_name: legalName,
        legal_id: legalId || undefined,
        contact_email: contactEmail || undefined,
        contact_phone: contactPhone || undefined,
      });
      onCreated(o);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not create owner.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-2 space-y-3 rounded-lg border border-border bg-surface p-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Stream</label>
          <select
            className="input"
            value={stream}
            onChange={(e) => setStream(e.target.value as Stream)}
          >
            {STREAMS.map((s) => (
              <option key={s} value={s}>
                {STREAM_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Legal ID</label>
          <input className="input" value={legalId} onChange={(e) => setLegalId(e.target.value)} />
        </div>
      </div>
      <div>
        <label className="label">Legal name</label>
        <input className="input" value={legalName} onChange={(e) => setLegalName(e.target.value)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Contact email</label>
          <input
            className="input"
            type="email"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="label">Contact phone</label>
          <input
            className="input"
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
          />
        </div>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={onCancel} className="btn-secondary flex-1">
          Cancel
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={legalName.length < 2 || busy}
          className="btn-primary flex-1"
        >
          {busy ? <InlineSpinner /> : "Create owner"}
        </button>
      </div>
    </div>
  );
}

function CreateZoneInline({
  propertyId,
  onCreated,
}: {
  propertyId: string;
  onCreated: (z: SensorZone) => void;
}) {
  const [building, setBuilding] = useState("");
  const [zone, setZone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const z = await zoneApi.create({
        property_id: propertyId,
        building_label: building,
        zone_label: zone,
      });
      onCreated(z);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not create zone.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-border bg-canvas p-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Building label</label>
          <input
            className="input"
            value={building}
            onChange={(e) => setBuilding(e.target.value)}
            placeholder="e.g. Block A"
          />
        </div>
        <div>
          <label className="label">Zone label</label>
          <input
            className="input"
            value={zone}
            onChange={(e) => setZone(e.target.value)}
            placeholder="e.g. Roof - HVAC"
          />
        </div>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
      <button
        type="button"
        onClick={submit}
        disabled={!building || !zone || busy}
        className="btn-primary w-full"
      >
        {busy ? <InlineSpinner /> : "Add zone"}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Success panel
// ---------------------------------------------------------------------------

function SuccessPanel({
  observation,
  onAnother,
}: {
  observation: Observation;
  onAnother: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl">
      <div className="card p-6 sm:p-8">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-6 w-6 flex-shrink-0 text-accent" />
          <div>
            <h2 className="text-lg font-semibold text-ink">Observation recorded</h2>
            <p className="mt-1 text-sm text-ink-muted">
              The entry has been chained at sequence #{observation.chain_sequence}.
            </p>
          </div>
        </div>

        <dl className="mt-6 space-y-4 border-t border-border pt-6 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Entry reference</dt>
            <dd>
              <EntryRefId refId={observation.entry_ref_id} copyable />
            </dd>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Severity</dt>
            <dd>
              <SeverityBadge severity={observation.severity} />
            </dd>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Property</dt>
            <dd className="text-right text-ink">
              {observation.property_name}
              <div className="text-xs text-ink-subtle">
                {observation.building_label} · {observation.zone_label}
              </div>
            </dd>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Entry hash</dt>
            <dd>
              <HashDisplay hash={observation.entry_hash} />
            </dd>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Linked to previous</dt>
            <dd>
              <HashDisplay hash={observation.prev_hash} />
            </dd>
          </div>
        </dl>

        <div className="mt-6 flex flex-col gap-2 sm:flex-row">
          <Link
            to={`/observations/${observation.id}`}
            className="btn-secondary flex-1 justify-center"
          >
            View detail
          </Link>
          <button onClick={onAnother} className="btn-primary flex-1 justify-center">
            Submit another
          </button>
        </div>
      </div>
    </div>
  );
}
