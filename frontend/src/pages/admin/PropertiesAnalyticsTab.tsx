import {
  ChevronDown,
  Download,
  Eye,
  EyeOff,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { EmptyState } from "../../components/EmptyState";
import { LoadingState } from "../../components/LoadingState";
import { admin as adminApi } from "../../lib/api";
import { exportToXlsx, timestampedFilename } from "../../lib/xlsx";
import type {
  DashboardResponse,
  DashboardZoneRow,
  Severity,
  Stream,
} from "../../types/api";
import { STREAM_LABELS } from "../../types/api";

// ---------------------------------------------------------------------------
// Column definitions — single source of truth for both UI and Excel export.
// ---------------------------------------------------------------------------

interface Col {
  id: string;
  header: string;
  width?: number;
  cell: (r: DashboardZoneRow) => React.ReactNode;
  /** Excel-friendly value. SheetJS handles Date natively. */
  excel: (r: DashboardZoneRow) => string | number | boolean | Date | null;
  defaultVisible?: boolean;
}

function fmtMoney(v: string | null): string {
  if (v === null || v === undefined) return "";
  const n = Number(v);
  if (isNaN(n)) return "";
  return n.toLocaleString();
}

function fmtRelativeDays(days: number | null): string {
  if (days === null || days === undefined) return "—";
  if (days === 0) return "today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

const SEVERITY_PILL: Record<Severity, string> = {
  Normal: "bg-accent-50 text-accent-700",
  Watch: "bg-warning-50 text-warning-700",
  Alert: "bg-danger-50 text-danger-700",
};

const ALL_COLUMNS: Col[] = [
  {
    id: "stream",
    header: "Stream",
    width: 14,
    cell: (r) => (
      <span className="capitalize">{STREAM_LABELS[r.stream]}</span>
    ),
    excel: (r) => STREAM_LABELS[r.stream],
  },
  {
    id: "owner_name",
    header: "Client name",
    width: 22,
    cell: (r) => r.owner_name,
    excel: (r) => r.owner_name,
  },
  {
    id: "owner_id",
    header: "Client ID",
    width: 38,
    cell: (r) => <code className="mono text-xs">{r.owner_id}</code>,
    excel: (r) => r.owner_id,
  },
  {
    id: "kyc_status",
    header: "KYC",
    width: 10,
    cell: (r) => <span className="capitalize">{r.kyc_status}</span>,
    excel: (r) => r.kyc_status,
  },
  {
    id: "property_name",
    header: "Property",
    width: 22,
    cell: (r) => r.property_name,
    excel: (r) => r.property_name,
  },
  {
    id: "city",
    header: "City",
    width: 14,
    cell: (r) => r.city || "—",
    excel: (r) => r.city || "",
  },
  {
    id: "property_status",
    header: "Property status",
    width: 14,
    cell: (r) => <span className="capitalize">{r.property_status}</span>,
    excel: (r) => r.property_status,
  },
  {
    id: "land_value",
    header: "Land value (RM)",
    width: 16,
    cell: (r) => fmtMoney(r.land_value),
    excel: (r) => (r.land_value ? Number(r.land_value) : null),
  },
  {
    id: "structure_value",
    header: "Structure value (RM)",
    width: 18,
    cell: (r) => fmtMoney(r.structure_value),
    excel: (r) => (r.structure_value ? Number(r.structure_value) : null),
  },
  {
    id: "building_label",
    header: "Building",
    width: 14,
    cell: (r) => r.building_label,
    excel: (r) => r.building_label,
  },
  {
    id: "zone_label",
    header: "Sensor location",
    width: 22,
    cell: (r) => r.zone_label,
    excel: (r) => r.zone_label,
  },
  {
    id: "zone_active",
    header: "Zone active",
    width: 10,
    cell: (r) =>
      r.zone_active ? (
        <span className="text-accent-700">✓</span>
      ) : (
        <span className="text-ink-subtle">✗</span>
      ),
    excel: (r) => r.zone_active,
  },
  {
    id: "total_observations",
    header: "Total obs.",
    width: 10,
    cell: (r) => <span className="mono">{r.total_observations}</span>,
    excel: (r) => r.total_observations,
  },
  {
    id: "normal_count",
    header: "Normal",
    width: 8,
    cell: (r) => <span className="mono text-accent-700">{r.normal_count}</span>,
    excel: (r) => r.normal_count,
  },
  {
    id: "watch_count",
    header: "Watch",
    width: 8,
    cell: (r) => <span className="mono text-warning-700">{r.watch_count}</span>,
    excel: (r) => r.watch_count,
  },
  {
    id: "alert_count",
    header: "Alert",
    width: 8,
    cell: (r) => <span className="mono text-danger-700">{r.alert_count}</span>,
    excel: (r) => r.alert_count,
  },
  {
    id: "reviewed_count",
    header: "Reviewed",
    width: 10,
    cell: (r) => <span className="mono">{r.reviewed_count}</span>,
    excel: (r) => r.reviewed_count,
  },
  {
    id: "voided_count",
    header: "Voided",
    width: 8,
    cell: (r) => <span className="mono text-danger-700/70">{r.voided_count}</span>,
    excel: (r) => r.voided_count,
  },
  {
    id: "last_submitted_at",
    header: "Last submission",
    width: 18,
    cell: (r) =>
      r.last_submitted_at
        ? new Date(r.last_submitted_at).toLocaleDateString()
        : "—",
    excel: (r) =>
      r.last_submitted_at ? new Date(r.last_submitted_at) : null,
  },
  {
    id: "last_severity",
    header: "Last severity",
    width: 12,
    cell: (r) =>
      r.last_severity ? (
        <span className={`pill ${SEVERITY_PILL[r.last_severity]}`}>
          {r.last_severity}
        </span>
      ) : (
        "—"
      ),
    excel: (r) => r.last_severity || "",
  },
  {
    id: "last_submitted_by_name",
    header: "Last submitted by",
    width: 18,
    cell: (r) => r.last_submitted_by_name || "—",
    excel: (r) => r.last_submitted_by_name || "",
  },
  {
    id: "days_since_last",
    header: "Days since last",
    width: 14,
    cell: (r) => fmtRelativeDays(r.days_since_last),
    excel: (r) => r.days_since_last,
  },
];

const DEFAULT_VISIBLE = new Set(ALL_COLUMNS.map((c) => c.id));

const STREAMS: Stream[] = [
  "reit",
  "lender",
  "individual",
  "insurer",
  "government",
  "family_office",
  "developer",
];
const SEVERITIES: Severity[] = ["Normal", "Watch", "Alert"];

// ---------------------------------------------------------------------------
// Group-by support
// ---------------------------------------------------------------------------

type GroupBy = "none" | "stream" | "client" | "property" | "severity";

interface GroupedRow {
  key: string;
  label: string;
  count: number;
  totalObservations: number;
  alerts: number;
  watches: number;
  voided: number;
}

function groupRows(rows: DashboardZoneRow[], groupBy: GroupBy): GroupedRow[] {
  if (groupBy === "none") return [];
  const map = new Map<string, GroupedRow>();
  for (const r of rows) {
    let key: string;
    let label: string;
    switch (groupBy) {
      case "stream":
        key = r.stream;
        label = STREAM_LABELS[r.stream];
        break;
      case "client":
        key = r.owner_id;
        label = r.owner_name;
        break;
      case "property":
        key = r.property_id;
        label = r.property_name;
        break;
      case "severity":
        key = r.last_severity || "_none";
        label = r.last_severity || "(no observations)";
        break;
      default:
        key = "_";
        label = "";
    }
    let g = map.get(key);
    if (!g) {
      g = {
        key,
        label,
        count: 0,
        totalObservations: 0,
        alerts: 0,
        watches: 0,
        voided: 0,
      };
      map.set(key, g);
    }
    g.count += 1;
    g.totalObservations += r.total_observations;
    g.alerts += r.alert_count;
    g.watches += r.watch_count;
    g.voided += r.voided_count;
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PropertiesAnalyticsTab() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [search, setSearch] = useState("");
  const [streamFilter, setStreamFilter] = useState<Stream[]>([]);
  const [severityFilter, setSeverityFilter] = useState<Severity[]>([]);

  // View state
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [visibleCols, setVisibleCols] = useState<Set<string>>(
    new Set(DEFAULT_VISIBLE)
  );
  const [colMenuOpen, setColMenuOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Sort state
  const [sortKey, setSortKey] = useState<string>("owner_name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  // Debounce search
  const debounceRef = useRef<number | null>(null);
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    adminApi
      .dashboardProperties({
        stream: streamFilter.length ? streamFilter : undefined,
        severity: severityFilter.length ? severityFilter : undefined,
        search: debouncedSearch || undefined,
      })
      .then((res) => {
        if (cancelled) return;
        setData(res);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.response?.data?.detail || "Failed to load dashboard.");
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [streamFilter, severityFilter, debouncedSearch]);

  const rows = data?.rows ?? [];

  // Apply sort client-side
  const sortedRows = useMemo(() => {
    const col = ALL_COLUMNS.find((c) => c.id === sortKey);
    if (!col) return rows;
    const copy = [...rows];
    copy.sort((a, b) => {
      const av = col.excel(a);
      const bv = col.excel(b);
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  const grouped = useMemo(() => groupRows(sortedRows, groupBy), [sortedRows, groupBy]);

  const visibleColumnList = ALL_COLUMNS.filter((c) => visibleCols.has(c.id));

  function toggleCol(id: string) {
    setVisibleCols((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function resetCols() {
    setVisibleCols(new Set(DEFAULT_VISIBLE));
  }

  function clickHeader(id: string) {
    if (sortKey === id) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(id);
      setSortDir("asc");
    }
  }

  function exportCurrentView() {
    exportToXlsx({
      filename: timestampedFilename("twinval-properties-current"),
      sheetName: "Properties (current view)",
      columns: visibleColumnList.map((c) => ({
        header: c.header,
        value: c.excel,
        width: c.width,
      })),
      rows: sortedRows,
    });
  }

  async function exportAllData() {
    setExporting(true);
    try {
      const all = await adminApi.dashboardProperties({ all: true });
      exportToXlsx({
        filename: timestampedFilename("twinval-properties-full"),
        sheetName: "Properties (all)",
        columns: ALL_COLUMNS.map((c) => ({
          header: c.header,
          value: c.excel,
          width: c.width,
        })),
        rows: all.rows,
      });
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  function clearFilters() {
    setSearch("");
    setStreamFilter([]);
    setSeverityFilter([]);
  }

  const filtersActive =
    search.length > 0 || streamFilter.length > 0 || severityFilter.length > 0;

  return (
    <div>
      {/* Counters strip */}
      <div className="card mb-4 grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
        <Counter
          label="Sensor zones"
          shown={data?.total_zones ?? 0}
          total={data?.total_zones_unfiltered ?? 0}
        />
        <Counter
          label="Properties"
          shown={data?.total_properties ?? 0}
          total={data?.total_properties_unfiltered ?? 0}
        />
        <Counter
          label="Observations"
          shown={data?.total_observations ?? 0}
          total={data?.total_observations_unfiltered ?? 0}
        />
        <Counter
          label="Visible columns"
          shown={visibleColumnList.length}
          total={ALL_COLUMNS.length}
        />
      </div>

      {/* Toolbar */}
      <div className="card mb-4 p-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search */}
          <div className="relative min-w-[220px] flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
            <input
              type="text"
              className="input pl-9"
              placeholder="Search property, owner, building, zone…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* Group by */}
          <div className="flex items-center gap-2 text-sm">
            <label className="text-ink-muted">Group by</label>
            <select
              className="input !w-auto !py-1.5"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
            >
              <option value="none">None</option>
              <option value="stream">Stream</option>
              <option value="client">Client</option>
              <option value="property">Property</option>
              <option value="severity">Last severity</option>
            </select>
          </div>

          {/* Column menu */}
          <div className="relative">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setColMenuOpen((s) => !s)}
            >
              <Eye className="h-4 w-4" /> Columns ({visibleColumnList.length}/
              {ALL_COLUMNS.length})
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
            {colMenuOpen && (
              <div className="absolute right-0 z-20 mt-2 w-72 rounded-lg border border-border bg-surface p-2 shadow-elevated">
                <div className="mb-2 flex items-center justify-between border-b border-border px-2 pb-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">
                    Show columns
                  </span>
                  <button
                    type="button"
                    onClick={resetCols}
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    <RotateCcw className="h-3 w-3" /> Reset
                  </button>
                </div>
                <div className="max-h-72 overflow-y-auto">
                  {ALL_COLUMNS.map((c) => {
                    const on = visibleCols.has(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => toggleCol(c.id)}
                        className="flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-canvas"
                      >
                        <span className="text-ink">{c.header}</span>
                        {on ? (
                          <Eye className="h-4 w-4 text-primary" />
                        ) : (
                          <EyeOff className="h-4 w-4 text-ink-subtle" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Exports */}
          <div className="flex gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={exportCurrentView}
              disabled={loading || sortedRows.length === 0}
            >
              <Download className="h-4 w-4" /> Current view
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={exportAllData}
              disabled={exporting}
            >
              <Download className="h-4 w-4" />
              {exporting ? "Exporting…" : "All data"}
            </button>
          </div>
        </div>

        {/* Filter chips */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
            Stream:
          </span>
          {STREAMS.map((s) => {
            const on = streamFilter.includes(s);
            return (
              <button
                key={s}
                type="button"
                onClick={() =>
                  setStreamFilter((f) =>
                    on ? f.filter((x) => x !== s) : [...f, s]
                  )
                }
                className={`pill cursor-pointer ${
                  on
                    ? "bg-primary text-white border border-primary"
                    : "bg-surface text-ink-muted border border-border hover:border-primary/40"
                }`}
              >
                {STREAM_LABELS[s]}
              </button>
            );
          })}

          <span className="ml-3 text-xs font-medium uppercase tracking-wide text-ink-subtle">
            Severity:
          </span>
          {SEVERITIES.map((s) => {
            const on = severityFilter.includes(s);
            return (
              <button
                key={s}
                type="button"
                onClick={() =>
                  setSeverityFilter((f) =>
                    on ? f.filter((x) => x !== s) : [...f, s]
                  )
                }
                className={`pill cursor-pointer ${
                  on
                    ? "bg-primary text-white border border-primary"
                    : "bg-surface text-ink-muted border border-border hover:border-primary/40"
                }`}
              >
                {s}
              </button>
            );
          })}

          {filtersActive && (
            <button
              type="button"
              onClick={clearFilters}
              className="ml-auto inline-flex items-center gap-1 text-xs text-ink-muted hover:text-ink"
            >
              <X className="h-3 w-3" /> Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Table or grouped view */}
      {error ? (
        <div className="card p-4 text-sm text-danger-700">{error}</div>
      ) : loading ? (
        <LoadingState />
      ) : sortedRows.length === 0 ? (
        <EmptyState
          title={
            filtersActive
              ? "No zones match the current filters"
              : "No sensor zones enrolled yet"
          }
          message={
            filtersActive
              ? "Try clearing filters, or widen the search."
              : "Enrol a property and add a sensor zone to see analytics here."
          }
        />
      ) : groupBy !== "none" ? (
        <GroupedView grouped={grouped} groupBy={groupBy} />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-canvas">
                <tr>
                  {visibleColumnList.map((c) => {
                    const isSorted = sortKey === c.id;
                    return (
                      <th
                        key={c.id}
                        onClick={() => clickHeader(c.id)}
                        className={`cursor-pointer whitespace-nowrap px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide ${
                          isSorted ? "text-primary" : "text-ink-subtle"
                        }`}
                      >
                        {c.header}
                        {isSorted && (
                          <span className="ml-1">
                            {sortDir === "asc" ? "▲" : "▼"}
                          </span>
                        )}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sortedRows.map((r) => (
                  <tr key={r.zone_id} className="text-sm hover:bg-canvas">
                    {visibleColumnList.map((c) => (
                      <td key={c.id} className="whitespace-nowrap px-4 py-2.5">
                        {c.cell(r)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Counter({
  label,
  shown,
  total,
}: {
  label: string;
  shown: number;
  total: number;
}) {
  const filtered = shown !== total;
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold text-ink">
          {shown.toLocaleString()}
        </span>
        {filtered && (
          <span className="text-xs text-ink-muted">
            of {total.toLocaleString()}
          </span>
        )}
      </div>
    </div>
  );
}

function GroupedView({
  grouped,
  groupBy,
}: {
  grouped: GroupedRow[];
  groupBy: GroupBy;
}) {
  return (
    <div className="card overflow-hidden">
      <table className="min-w-full">
        <thead className="bg-canvas">
          <tr>
            <th className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-ink-subtle">
              {groupBy === "stream"
                ? "Stream"
                : groupBy === "client"
                ? "Client"
                : groupBy === "property"
                ? "Property"
                : "Last severity"}
            </th>
            <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-ink-subtle">
              Zones
            </th>
            <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-ink-subtle">
              Observations
            </th>
            <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-ink-subtle">
              Watch
            </th>
            <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-ink-subtle">
              Alert
            </th>
            <th className="px-4 py-2.5 text-right text-xs font-medium uppercase tracking-wide text-ink-subtle">
              Voided
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {grouped.map((g) => (
            <tr key={g.key} className="text-sm">
              <td className="px-4 py-2.5 font-medium text-ink">{g.label}</td>
              <td className="px-4 py-2.5 text-right mono">{g.count}</td>
              <td className="px-4 py-2.5 text-right mono">{g.totalObservations}</td>
              <td className="px-4 py-2.5 text-right mono text-warning-700">
                {g.watches}
              </td>
              <td className="px-4 py-2.5 text-right mono text-danger-700">
                {g.alerts}
              </td>
              <td className="px-4 py-2.5 text-right mono text-ink-subtle">
                {g.voided}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
