import { ChevronLeft, ChevronRight, FileQuestion } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { EntryRefId } from "../components/EntryRefId";
import { HashDisplay } from "../components/HashDisplay";
import { LoadingState } from "../components/LoadingState";
import { SeverityBadge } from "../components/SeverityBadge";
import { observations as obsApi } from "../lib/api";
import { formatDateShort } from "../lib/format";
import type { ObservationListItem, Severity } from "../types/api";

const PAGE_SIZE = 20;

export function HistoryPage() {
  const [items, setItems] = useState<ObservationListItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    obsApi
      .list({
        limit: PAGE_SIZE,
        offset,
        severity: severityFilter || undefined,
      })
      .then((page) => {
        if (cancelled) return;
        setItems(page.items);
        setTotal(page.total);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.response?.data?.detail || "Failed to load history.");
      });
    return () => {
      cancelled = true;
    };
  }, [offset, severityFilter]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Observation History</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Every entry you've submitted, in chain order.
          </p>
        </div>
        <Link to="/submit" className="btn-primary">
          New Observation
        </Link>
      </div>

      {/* Filter chips */}
      <div className="mb-4 flex flex-wrap gap-2">
        <FilterChip
          active={severityFilter === null}
          onClick={() => {
            setSeverityFilter(null);
            setOffset(0);
          }}
        >
          All
        </FilterChip>
        {(["Normal", "Watch", "Alert"] as Severity[]).map((s) => (
          <FilterChip
            key={s}
            active={severityFilter === s}
            onClick={() => {
              setSeverityFilter(s);
              setOffset(0);
            }}
          >
            {s}
          </FilterChip>
        ))}
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {error ? (
          <div className="px-5 py-4 text-sm text-danger-700">{error}</div>
        ) : items === null ? (
          <LoadingState />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<FileQuestion className="h-8 w-8" />}
            title="No observations match this filter"
            message="Try a different severity, or submit a new observation."
            action={
              <Link to="/submit" className="btn-primary">
                Submit observation
              </Link>
            }
          />
        ) : (
          <>
            {/* Desktop table */}
            <table className="hidden w-full md:table">
              <thead className="bg-canvas">
                <tr className="text-left text-xs font-medium uppercase tracking-wide text-ink-subtle">
                  <th className="px-5 py-3">Reference</th>
                  <th className="px-5 py-3">Submitted</th>
                  <th className="px-5 py-3">Property / Zone</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">Severity</th>
                  <th className="px-5 py-3">Hash</th>
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
                    <td className="px-5 py-3 text-ink-muted">{formatDateShort(row.submitted_at)}</td>
                    <td className="px-5 py-3">
                      <div className="font-medium text-ink">{row.property_name}</div>
                      <div className="text-xs text-ink-subtle">
                        {row.building_label} · {row.zone_label}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-ink-muted">{row.observation_type}</td>
                    <td className="px-5 py-3">
                      <SeverityBadge severity={row.severity} />
                    </td>
                    <td className="px-5 py-3">
                      <HashDisplay hash={row.entry_hash} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Mobile list */}
            <ul className="divide-y divide-border md:hidden">
              {items.map((row) => (
                <li key={row.id}>
                  <Link
                    to={`/observations/${row.id}`}
                    className="block px-4 py-3.5 hover:bg-canvas"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <EntryRefId refId={row.entry_ref_id} />
                      <SeverityBadge severity={row.severity} />
                    </div>
                    <div className="mt-1 text-sm text-ink">
                      {row.property_name}
                      <span className="text-ink-subtle">
                        {" "}
                        · {row.building_label} / {row.zone_label}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-xs text-ink-muted">
                      <span>
                        {row.observation_type} · {formatDateShort(row.submitted_at)}
                      </span>
                      <HashDisplay hash={row.entry_hash} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>

            {/* Pagination */}
            <div className="flex items-center justify-between border-t border-border bg-canvas px-5 py-3 text-sm">
              <span className="text-ink-muted">
                Page {currentPage} of {totalPages} · {total} total
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

function FilterChip({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
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
