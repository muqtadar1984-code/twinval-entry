import { AlertTriangle, ArrowRight, ClipboardList, Eye, FileQuestion } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { EntryRefId } from "../components/EntryRefId";
import { LoadingState } from "../components/LoadingState";
import { SeverityBadge } from "../components/SeverityBadge";
import { useAuth } from "../contexts/AuthContext";
import { observations as obsApi } from "../lib/api";
import { formatDateShort } from "../lib/format";
import type { ObservationListItem } from "../types/api";

export function DashboardPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<ObservationListItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    obsApi
      .list({ limit: 100, offset: 0 })
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
  }, []);

  const stats = useMemo(() => {
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const list = items || [];
    return {
      total,
      week: list.filter((i) => new Date(i.submitted_at) >= sevenDaysAgo).length,
      alerts: list.filter((i) => i.severity === "Alert").length,
      watch: list.filter((i) => i.severity === "Watch").length,
    };
  }, [items, total]);

  const recent = (items || []).slice(0, 5);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">
            Welcome back, {user?.name?.split(" ")[0] || "there"}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Your contributions feed TwinVal's Confidence Index for IIUM properties.
          </p>
        </div>
        <Link to="/submit" className="btn-primary">
          <ClipboardList className="h-4 w-4" />
          New Observation
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        <StatCard label="Total submissions" value={stats.total} />
        <StatCard label="This week" value={stats.week} />
        <StatCard label="Alerts" value={stats.alerts} accent="danger" />
        <StatCard label="Watch" value={stats.watch} accent="warning" />
      </div>

      {/* Recent */}
      <section className="mt-8 card">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-base font-semibold text-ink">Recent observations</h2>
          {recent.length > 0 && (
            <Link
              to="/history"
              className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>

        {error ? (
          <div className="px-5 py-4 text-sm text-danger-700">{error}</div>
        ) : items === null ? (
          <LoadingState />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={<FileQuestion className="h-8 w-8" />}
            title="No observations submitted yet"
            message="Your first submission will initialise the observation chain for this deployment."
            action={
              <Link to="/submit" className="btn-primary">
                Submit first observation
              </Link>
            }
          />
        ) : (
          <ul className="divide-y divide-border">
            {recent.map((entry) => (
              <li key={entry.id}>
                <Link
                  to={`/observations/${entry.id}`}
                  className="flex items-start justify-between gap-3 px-5 py-3.5 hover:bg-canvas"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <EntryRefId refId={entry.entry_ref_id} />
                      <SeverityBadge severity={entry.severity} />
                      {entry.reviewed && (
                        <span className="pill border border-border bg-canvas text-ink-muted">
                          <Eye className="h-3 w-3" /> reviewed
                        </span>
                      )}
                    </div>
                    <div className="mt-1 truncate text-sm text-ink">
                      <span className="font-medium">{entry.property_name}</span>
                      <span className="text-ink-subtle"> · {entry.building_label} / {entry.zone_label}</span>
                    </div>
                    <div className="mt-0.5 text-xs text-ink-muted">
                      {entry.observation_type} · {formatDateShort(entry.submitted_at)}
                    </div>
                  </div>
                  <ArrowRight className="mt-2 h-4 w-4 flex-shrink-0 text-ink-subtle" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "danger" | "warning";
}) {
  const valueColor =
    accent === "danger"
      ? "text-danger"
      : accent === "warning"
      ? "text-warning"
      : "text-ink";
  return (
    <div className="card p-4 sm:p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </div>
      <div className={`mt-1 text-2xl font-semibold ${valueColor}`}>
        {value}
        {accent === "danger" && value > 0 && (
          <AlertTriangle className="ml-1 inline-block h-4 w-4 text-danger" />
        )}
      </div>
    </div>
  );
}
