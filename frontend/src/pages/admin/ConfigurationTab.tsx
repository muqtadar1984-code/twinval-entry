import { Building2, ChevronDown, MapPin, Users } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { InlineSpinner, LoadingState } from "../../components/LoadingState";
import { ownerProfiles as ownerApi, properties as propApi, sensorZones as zoneApi } from "../../lib/api";
import { formatDateShort } from "../../lib/format";
import type { KycStatus, OwnerProfile, Property, SensorZone } from "../../types/api";
import { STREAM_LABELS } from "../../types/api";

type Section = "owners" | "properties" | "zones";

export function AdminConfigurationTab() {
  const [section, setSection] = useState<Section>("owners");

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        <SectionChip active={section === "owners"} onClick={() => setSection("owners")}>
          <Users className="h-3.5 w-3.5" /> Owner Profiles
        </SectionChip>
        <SectionChip active={section === "properties"} onClick={() => setSection("properties")}>
          <Building2 className="h-3.5 w-3.5" /> Properties
        </SectionChip>
        <SectionChip active={section === "zones"} onClick={() => setSection("zones")}>
          <MapPin className="h-3.5 w-3.5" /> Sensor Zones
        </SectionChip>
      </div>

      {section === "owners" && <OwnersList />}
      {section === "properties" && <PropertiesList />}
      {section === "zones" && <ZonesList />}
    </div>
  );
}

function SectionChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`pill cursor-pointer transition ${
        active
          ? "bg-primary text-white border border-primary"
          : "bg-surface text-ink-muted border border-border hover:border-primary/40"
      }`}
    >
      {children}
    </button>
  );
}

const KYC_PILL: Record<KycStatus, string> = {
  verified: "bg-accent-50 text-accent-700 border border-accent/30",
  failed: "bg-danger-50 text-danger-700 border border-danger/30",
  pending: "bg-warning-50 text-warning-700 border border-warning/30",
};

const KYC_OPTIONS: KycStatus[] = ["pending", "verified", "failed"];

function OwnersList() {
  const [items, setItems] = useState<OwnerProfile[] | null>(null);
  useEffect(() => {
    ownerApi
      .list({ limit: 200 })
      .then((p) => setItems(p.items))
      .catch(() => setItems([]));
  }, []);

  function patchOwner(updated: OwnerProfile) {
    setItems((prev) =>
      prev ? prev.map((o) => (o.id === updated.id ? updated : o)) : prev
    );
  }

  if (items === null) return <LoadingState />;

  return (
    <div className="card overflow-hidden">
      <div className="border-b border-border px-5 py-4 text-sm font-semibold text-ink">
        {items.length} owner profile{items.length === 1 ? "" : "s"}
      </div>
      <ul className="divide-y divide-border">
        {items.map((o) => (
          <li key={o.id} className="px-5 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-medium text-ink">{o.legal_name}</div>
                <div className="mt-0.5 text-xs text-ink-subtle">
                  {STREAM_LABELS[o.stream]}
                  {o.legal_id ? ` · ${o.legal_id}` : ""}
                  {o.contact_email ? ` · ${o.contact_email}` : ""}
                </div>
              </div>
              <KycEditor owner={o} onUpdated={patchOwner} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function KycEditor({
  owner,
  onUpdated,
}: {
  owner: OwnerProfile;
  onUpdated: (o: OwnerProfile) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  // Click-outside to close
  useEffect(() => {
    if (!open) return;
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [open]);

  async function setKyc(status: KycStatus) {
    if (status === owner.kyc_status) {
      setOpen(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await ownerApi.update(owner.id, { kyc_status: status });
      onUpdated(updated);
      setOpen(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not update KYC.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((s) => !s)}
        className={`pill cursor-pointer transition ${KYC_PILL[owner.kyc_status]} hover:brightness-95`}
        title="Click to update KYC status"
      >
        KYC: {owner.kyc_status}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-border bg-surface p-1.5 shadow-elevated">
          <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink-subtle">
            Update KYC status
          </div>
          {KYC_OPTIONS.map((status) => {
            const current = status === owner.kyc_status;
            return (
              <button
                key={status}
                type="button"
                onClick={() => setKyc(status)}
                disabled={busy}
                className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-canvas ${
                  current ? "font-semibold text-primary" : "text-ink"
                }`}
              >
                <span className="capitalize">{status}</span>
                {busy && status !== owner.kyc_status ? (
                  <InlineSpinner className="h-3.5 w-3.5" />
                ) : current ? (
                  <span className="text-xs text-ink-subtle">current</span>
                ) : null}
              </button>
            );
          })}
          {error && (
            <p className="px-2 pt-1 text-xs text-danger">{error}</p>
          )}
        </div>
      )}
    </div>
  );
}

function PropertiesList() {
  const [items, setItems] = useState<Property[] | null>(null);
  useEffect(() => {
    propApi
      .list({ limit: 200 })
      .then((p) => setItems(p.items))
      .catch(() => setItems([]));
  }, []);

  if (items === null) return <LoadingState />;

  return (
    <div className="card overflow-hidden">
      <div className="border-b border-border px-5 py-4 text-sm font-semibold text-ink">
        {items.length} propert{items.length === 1 ? "y" : "ies"}
      </div>
      <ul className="divide-y divide-border">
        {items.map((p) => (
          <li key={p.id} className="px-5 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-medium text-ink">{p.name}</div>
                <div className="mt-0.5 text-xs text-ink-subtle">
                  {p.address}
                  {p.city ? `, ${p.city}` : ""}
                  {p.country ? `, ${p.country}` : ""}
                </div>
                <div className="mt-1 text-xs text-ink-muted">
                  {p.primary_owner_name} · {STREAM_LABELS[p.primary_owner_stream]}
                </div>
              </div>
              <span
                className={`pill ${
                  p.status === "active"
                    ? "bg-accent-50 text-accent-700"
                    : "bg-canvas text-ink-muted border border-border"
                }`}
              >
                {p.status}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ZonesList() {
  const [properties, setProperties] = useState<Property[] | null>(null);
  const [propertyId, setPropertyId] = useState<string>("");
  const [zones, setZones] = useState<SensorZone[] | null>(null);

  useEffect(() => {
    propApi
      .list({ limit: 200 })
      .then((p) => {
        setProperties(p.items);
        if (p.items.length > 0) setPropertyId(p.items[0].id);
      })
      .catch(() => setProperties([]));
  }, []);

  useEffect(() => {
    if (!propertyId) {
      setZones([]);
      return;
    }
    setZones(null);
    zoneApi
      .list(propertyId, { limit: 500 })
      .then((p) => setZones(p.items))
      .catch(() => setZones([]));
  }, [propertyId]);

  if (properties === null) return <LoadingState />;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="text-sm text-ink-muted">Property:</label>
        <select
          className="input max-w-md"
          value={propertyId}
          onChange={(e) => setPropertyId(e.target.value)}
        >
          {properties.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      <div className="card overflow-hidden">
        {zones === null ? (
          <LoadingState />
        ) : zones.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-ink-muted">
            No sensor zones for this property.
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {zones.map((z) => (
              <li key={z.id} className="flex items-center justify-between px-5 py-3 text-sm">
                <div>
                  <span className="font-medium text-ink">{z.building_label}</span>
                  <span className="text-ink-subtle"> · {z.zone_label}</span>
                  <div className="mt-0.5 text-xs text-ink-subtle">
                    Created {formatDateShort(z.created_at)}
                  </div>
                </div>
                <span
                  className={`pill ${
                    z.is_active
                      ? "bg-accent-50 text-accent-700"
                      : "bg-canvas text-ink-muted border border-border"
                  }`}
                >
                  {z.is_active ? "active" : "inactive"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
