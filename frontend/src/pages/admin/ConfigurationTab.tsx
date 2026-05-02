import { Building2, MapPin, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { LoadingState } from "../../components/LoadingState";
import { ownerProfiles as ownerApi, properties as propApi, sensorZones as zoneApi } from "../../lib/api";
import { formatDateShort } from "../../lib/format";
import type { OwnerProfile, Property, SensorZone } from "../../types/api";
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

function OwnersList() {
  const [items, setItems] = useState<OwnerProfile[] | null>(null);
  useEffect(() => {
    ownerApi
      .list({ limit: 200 })
      .then((p) => setItems(p.items))
      .catch(() => setItems([]));
  }, []);

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
                </div>
              </div>
              <span
                className={`pill ${
                  o.kyc_status === "verified"
                    ? "bg-accent-50 text-accent-700"
                    : o.kyc_status === "failed"
                    ? "bg-danger-50 text-danger-700"
                    : "bg-warning-50 text-warning-700"
                }`}
              >
                KYC: {o.kyc_status}
              </span>
            </div>
          </li>
        ))}
      </ul>
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
