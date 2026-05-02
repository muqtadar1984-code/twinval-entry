import { ChevronLeft, ChevronRight, Download, Filter } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "../../components/EmptyState";
import { EntryRefId } from "../../components/EntryRefId";
import { HashDisplay } from "../../components/HashDisplay";
import { LoadingState } from "../../components/LoadingState";
import { SeverityBadge } from "../../components/SeverityBadge";
import { admin as adminApi } from "../../lib/api";
import { formatDateShort } from "../../lib/format";
import type { ObservationListItem, Severity, Stream } from "../../types/api";
import { STREAM_LABELS } from "../../types/api";

const PAGE_SIZE = 50;

type Filters = {
  severity: Severity | "";
  stream: Stream | "";
  reviewed: "" | "true" | "false";
  submitted_from: string;
  submitted_to: string;
};

export function AdminObservationsTab() {
  const [items, setItems] = useState<ObservationListItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({
    severity: "",
    stream: "",
    reviewed: "",
    submitted_from: "",
    submitted_to: "",
  });

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    adminApi
      .observations({
        limit: PAGE_SIZE,
        offset,
        severity: filters.severity || undefined,
        stream: filters.stream || undefined,
        reviewed:
          filters.reviewed === "true"
            ? true
            : filters.reviewed === "false"
            ? false
            : undefined,
        submitted_from: filters.submitted_from || undefined,
        submitted_to: filters.submitted_to || undefined,
      })
      .then((page) => {
        if (cancelled) return;
        setItems(page.items);
        setTotal(page.total);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.response?.data?.detail || "Failed to load observations.");
      });
    return () => {
      cancelled = true;
    };
  }, [offset, filters]);

  function exportCsv() {
    if (!items || items.length === 0) return;
    const header = [
      "entry_ref_id",
      "submitted_at",
      "property_name",
      "building_label",
      "zone_label",
      "owner_profile_name",
      "stream",
      "observation_type",
      "severity",
      "chain_sequence",
      "entry_hash",
      "reviewed",
    ];
    const rows = items.map((r) =>
      header
        .map((k) => {
          const v = (r as any)[k];
          const s = v === null || v === undefined ? "" : String(v);
          return `"${s.replace(/"/g, '""')}"`;
        })
        .join(",")
    );
    const csv = [header.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `twinval-observations-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function update<K extends keyof Filters>(key: K, value: Filters[K]) {
    setFilters((f) => ({ ...f, [key]: value }));
    setOffset(0);
  }

  return (
    <div>
      {/* Filters */}
      <div className="card p-4 sm:p-5">
        <div className="flex items-center gap-2 text-sm font-medium text-ink-muted">
          <Filter className="h-4 w-4" /> Filters
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 md:grid-cols-5">
          <div>
            <label className="label">Severity</label>
            <select
              className="input"
              value={filters.severity}
              onChange={(e) => update("severity", e.target.value as Filters["severity"])}
            >
              <option value="">All</option>
              <option value="Normal">Normal</option>
              <option value="Watch">Watch</option>
              <option value="Alert">Alert</option>
            </select>
          </div>
          <div>
            <label className="label">Stream</label>
            <select
              className="input"
              value={filters.stream}
              onChange={(e) => update("stream", e.target.value as Filters["stream"])}
            >
              <option value="">All</option>
              {Object.entries(STREAM_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Reviewed</label>
            <select
              className="input"
              value={filters.reviewed}
              onChange={(e) => update("reviewed", e.target.value as Filters["reviewed"])}
            >
              <option value="">Any</option>
              <option value="false">Not reviewed</option>
              <option value="true">Reviewed</option>
            </select>
          </div>
          <div>
            <label className="label">From</label>
            <input
              type="date"
              className="input"
              value={filters.submitted_from}
              onChange={(e) => update("submitted_from", e.target.value)}
            />
          </div>
          <div>
            <label className="label">To</label>
            <input
              type="date"
              className="input"
              value={filters.submitted_to}
              onChange={(e) => update("submitted_to", e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="mt-4 flex items-center justify-between">
        <div className="text-sm text-ink-muted">{total} entries</div>
        <button
          type="button"
          onClick={exportCsv}
          disabled={!items || items.length === 0}
          className="btn-secondary"
        >
          <Download className="h-4 w-4" /> Export CSV
        </button>
      </div>

      {/* Table */}
      <div className="mt-3 card overflow-hidden">
        {error ? (
          <div className="px-5 py-4 text-sm text-danger-700">{error}</div>
        ) : items === null ? (
          <LoadingState />
        ) : items.length === 0 ? (
          <EmptyState title="No matching observations" />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-canvas">
                  <tr className="text-left text-xs font-medium uppercase tracking-wide text-ink-subtle">
                    <th className="px-5 py-3">Reference</th>
                    <th className="px-5 py-3">Submitted</th>
                    <th className="px-5 py-3">Property / Owner</th>
                    <th className="px-5 py-3">Type</th>
                    <th className="px-5 py-3">Severity</th>
                    <th className="px-5 py-3">Hash</th>
                    <th className="px-5 py-3">Reviewed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((row) => (
                    <tr key={row.id} className="text-sm hover:bg-canvas">
                      <td className="px-5 py-3">
                        <Link to={`/observations/${row.id}`}>
                          <EntryRefId refId={row.entry_ref_id} />
                        </Link>
                      </td>
                      <td className="px-5 py-3 text-ink-muted">
                        {formatDateShort(row.submitted_at)}
                      </td>
                      <td className="px-5 py-3">
                        <div className="font-medium text-ink">{row.property_name}</div>
                        <div className="text-xs text-ink-subtle">
                          {row.owner_profile_name} · {STREAM_LABELS[row.stream]}
                        </div>
                      </td>
                      <td className="px-5 py-3 text-ink-muted">{row.observation_type}</td>
                      <td className="px-5 py-3">
                        <SeverityBadge severity={row.severity} />
                      </td>
                      <td className="px-5 py-3">
                        <HashDisplay hash={row.entry_hash} />
                      </td>
                      <td className="px-5 py-3 text-xs">
                        {row.reviewed ? (
                          <span className="text-accent-700">Yes</span>
                        ) : (
                          <span className="text-ink-subtle">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between border-t border-border bg-canvas px-5 py-3 text-sm">
              <span className="text-ink-muted">
                {offset + 1}–{Math.min(offset + items.length, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                  className="btn-secondary !px-2.5"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= total}
                  className="btn-secondary !px-2.5"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
