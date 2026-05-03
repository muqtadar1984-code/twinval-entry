import {
  AlertTriangle,
  ArrowRight,
  Camera,
  CameraOff,
  Clock,
  Eye,
  RefreshCcw,
  Timer,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EntryRefId } from "../../components/EntryRefId";
import { LoadingState } from "../../components/LoadingState";
import { SeverityBadge } from "../../components/SeverityBadge";
import { admin as adminApi } from "../../lib/api";
import { formatDateShort } from "../../lib/format";
import type {
  ActivityResponse,
  PendingReviewItem,
  StaleZoneItem,
  WeeklyBucket,
} from "../../types/api";

const STALE_PRESETS = [7, 14, 30, 60];

export function ActivityTab() {
  const [data, setData] = useState<ActivityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [staleDays, setStaleDays] = useState<number>(14);

  function load() {
    setLoading(true);
    setError(null);
    adminApi
      .activity({ stale_threshold_days: staleDays })
      .then((res) => setData(res))
      .catch((e) =>
        setError(e?.response?.data?.detail || "Failed to load activity.")
      )
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [staleDays]);

  if (loading && !data) return <LoadingState />;
  if (error) return <div className="card p-4 text-sm text-danger-700">{error}</div>;
  if (!data) return null;

  return (
    <div>
      {/* Top stat strip */}
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={<Clock className="h-4 w-4" />}
          label="Pending review"
          value={data.pending_review_total}
          accent={data.pending_review_total > 0 ? "warning" : "neutral"}
        />
        <StatCard
          icon={<Timer className="h-4 w-4" />}
          label={`Stale zones (${data.stale_threshold_days}d)`}
          value={data.stale_zones_total}
          accent={data.stale_zones_total > 0 ? "danger" : "neutral"}
        />
        <StatCard
          icon={
            data.photo_coverage.alert_coverage_pct >= 80 ? (
              <Camera className="h-4 w-4" />
            ) : (
              <CameraOff className="h-4 w-4" />
            )
          }
          label="Alert photos"
          value={`${data.photo_coverage.alert_coverage_pct}%`}
          subtext={`${data.photo_coverage.alerts_with_photo} of ${data.photo_coverage.total_alerts}`}
          accent={
            data.photo_coverage.total_alerts === 0
              ? "neutral"
              : data.photo_coverage.alert_coverage_pct >= 80
              ? "accent"
              : "warning"
          }
        />
        <StatCard
          icon={<RefreshCcw className="h-4 w-4" />}
          label="Last 7 days"
          value={data.submissions_last_7_days}
          subtext="submissions"
          accent="primary"
        />
      </div>

      {/* Trend chart */}
      <section className="card mb-4 p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">
            Submissions — last 12 weeks
          </h2>
          <Legend />
        </div>
        <WeeklyChart buckets={data.weekly_buckets} />
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Pending review */}
        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <h2 className="text-sm font-semibold text-ink">Pending review</h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                Watch + Alert entries waiting for an admin sign-off, oldest first.
              </p>
            </div>
            {data.pending_review.length > 0 && (
              <span className="pill border border-warning/30 bg-warning-50 text-warning-700">
                {data.pending_review_total}
              </span>
            )}
          </div>
          {data.pending_review.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-ink-muted">
              ✓ Nothing waiting. All Watch + Alert entries are reviewed.
            </div>
          ) : (
            <ul className="max-h-[480px] divide-y divide-border overflow-y-auto">
              {data.pending_review.map((p) => (
                <PendingRow key={p.entry_id} item={p} />
              ))}
            </ul>
          )}
        </section>

        {/* Stale zones */}
        <section className="card overflow-hidden">
          <div className="border-b border-border px-5 py-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink">Stale zones</h2>
              {data.stale_zones.length > 0 && (
                <span className="pill border border-danger/30 bg-danger-50 text-danger-700">
                  {data.stale_zones_total}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-ink-muted">
              Zones with no observations in the last
            </p>
            <div className="mt-2 flex gap-1">
              {STALE_PRESETS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setStaleDays(d)}
                  className={`pill cursor-pointer transition ${
                    staleDays === d
                      ? "bg-primary text-white border border-primary"
                      : "bg-surface text-ink-muted border border-border hover:border-primary/40"
                  }`}
                >
                  {d} days
                </button>
              ))}
            </div>
          </div>
          {data.stale_zones.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-ink-muted">
              ✓ Every zone has been observed within the threshold.
            </div>
          ) : (
            <ul className="max-h-[480px] divide-y divide-border overflow-y-auto">
              {data.stale_zones.map((z) => (
                <StaleZoneRow key={z.zone_id} item={z} />
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Photo coverage detail */}
      <section className="card mt-4 p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-ink">Photo coverage</h2>
            <p className="mt-0.5 text-xs text-ink-muted">
              Photos are the strongest audit evidence on Alert-severity entries.
            </p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <CoverageBar
            label="Alert entries"
            with_={data.photo_coverage.alerts_with_photo}
            total={data.photo_coverage.total_alerts}
            pct={data.photo_coverage.alert_coverage_pct}
            barColor="bg-danger"
          />
          <CoverageBar
            label="All live entries"
            with_={data.photo_coverage.observations_with_photo}
            total={data.photo_coverage.total_observations}
            pct={data.photo_coverage.overall_coverage_pct}
            barColor="bg-primary"
          />
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type Accent = "neutral" | "primary" | "accent" | "warning" | "danger";

function StatCard({
  icon,
  label,
  value,
  subtext,
  accent = "neutral",
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  subtext?: string;
  accent?: Accent;
}) {
  const valueColor = {
    neutral: "text-ink",
    primary: "text-primary",
    accent: "text-accent-700",
    warning: "text-warning-700",
    danger: "text-danger-700",
  }[accent];
  const iconBg = {
    neutral: "bg-canvas text-ink-muted",
    primary: "bg-primary-50 text-primary",
    accent: "bg-accent-50 text-accent-700",
    warning: "bg-warning-50 text-warning-700",
    danger: "bg-danger-50 text-danger-700",
  }[accent];

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
          {label}
        </div>
        <span
          className={`inline-flex h-7 w-7 items-center justify-center rounded-full ${iconBg}`}
        >
          {icon}
        </span>
      </div>
      <div className={`mt-2 text-2xl font-semibold ${valueColor}`}>{value}</div>
      {subtext && (
        <div className="mt-0.5 text-xs text-ink-muted">{subtext}</div>
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3 text-xs text-ink-muted">
      <LegendDot color="bg-accent" label="Normal" />
      <LegendDot color="bg-warning" label="Watch" />
      <LegendDot color="bg-danger" label="Alert" />
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

function WeeklyChart({ buckets }: { buckets: WeeklyBucket[] }) {
  const maxTotal = useMemo(
    () => Math.max(1, ...buckets.map((b) => b.total)),
    [buckets]
  );

  // SVG dimensions in viewport-relative units
  const W = 720;
  const H = 200;
  const PADDING_X = 16;
  const PADDING_TOP = 8;
  const PADDING_BOTTOM = 28;
  const chartW = W - PADDING_X * 2;
  const chartH = H - PADDING_TOP - PADDING_BOTTOM;
  const barW = (chartW / buckets.length) - 6;

  function shortLabel(weekStart: string): string {
    const d = new Date(weekStart);
    return `${d.toLocaleString("default", { month: "short" })} ${d.getDate()}`;
  }

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 480 }}>
        {/* axis baseline */}
        <line
          x1={PADDING_X}
          y1={H - PADDING_BOTTOM}
          x2={W - PADDING_X}
          y2={H - PADDING_BOTTOM}
          stroke="#E2E7EE"
          strokeWidth="1"
        />
        {buckets.map((b, i) => {
          const x = PADDING_X + i * (barW + 6) + 3;
          const baseY = H - PADDING_BOTTOM;
          const normalH = (b.normal / maxTotal) * chartH;
          const watchH = (b.watch / maxTotal) * chartH;
          const alertH = (b.alert / maxTotal) * chartH;

          const yNormal = baseY - normalH;
          const yWatch = yNormal - watchH;
          const yAlert = yWatch - alertH;

          return (
            <g key={b.week_start}>
              {b.total > 0 && (
                <>
                  <rect
                    x={x}
                    y={yNormal}
                    width={barW}
                    height={normalH}
                    fill="#2ECC71"
                    rx="2"
                  />
                  <rect
                    x={x}
                    y={yWatch}
                    width={barW}
                    height={watchH}
                    fill="#F39C12"
                    rx="2"
                  />
                  <rect
                    x={x}
                    y={yAlert}
                    width={barW}
                    height={alertH}
                    fill="#E74C3C"
                    rx="2"
                  />
                  <text
                    x={x + barW / 2}
                    y={yAlert - 4}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#5B6776"
                  >
                    {b.total}
                  </text>
                </>
              )}
              <text
                x={x + barW / 2}
                y={H - 8}
                textAnchor="middle"
                fontSize="10"
                fill="#8A95A4"
              >
                {shortLabel(b.week_start)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function PendingRow({ item }: { item: PendingReviewItem }) {
  return (
    <li className="hover:bg-canvas">
      <Link
        to={`/observations/${item.entry_id}`}
        className="flex items-start gap-3 px-5 py-3.5"
      >
        <SeverityBadge severity={item.severity} className="flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <EntryRefId refId={item.entry_ref_id} />
            <span className="pill border border-warning/30 bg-warning-50 text-warning-700">
              <Clock className="h-3 w-3" />
              waiting {item.days_waiting}d
            </span>
          </div>
          <div className="mt-0.5 truncate text-sm text-ink">
            {item.property_name}
            <span className="text-ink-subtle">
              {" "}· {item.building_label} / {item.zone_label}
            </span>
          </div>
          <div className="mt-1 line-clamp-2 text-xs text-ink-muted">
            {item.description_excerpt}
          </div>
          <div className="mt-1 text-[11px] text-ink-subtle">
            {item.observation_type} · by {item.intern_name} · {formatDateShort(item.submitted_at)}
          </div>
        </div>
        <ArrowRight className="mt-1 h-4 w-4 flex-shrink-0 text-ink-subtle" />
      </Link>
    </li>
  );
}

function StaleZoneRow({ item }: { item: StaleZoneItem }) {
  return (
    <li className="px-5 py-3.5 hover:bg-canvas">
      <div className="flex items-start gap-3">
        {item.never_observed ? (
          <span className="pill border border-danger/30 bg-danger-50 text-danger-700 flex-shrink-0">
            <AlertTriangle className="h-3 w-3" />
            never
          </span>
        ) : (
          <span className="pill border border-warning/30 bg-warning-50 text-warning-700 flex-shrink-0">
            <Timer className="h-3 w-3" />
            {item.days_stale}d
          </span>
        )}
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-ink">
            {item.property_name}
            <span className="font-normal text-ink-subtle">
              {" "}· {item.building_label} / {item.zone_label}
            </span>
          </div>
          <div className="mt-0.5 text-xs text-ink-muted">
            {item.owner_name}
            {item.last_submitted_at &&
              ` · last: ${formatDateShort(item.last_submitted_at)}`}
          </div>
        </div>
      </div>
    </li>
  );
}

function CoverageBar({
  label,
  with_,
  total,
  pct,
  barColor,
}: {
  label: string;
  with_: number;
  total: number;
  pct: number;
  barColor: string;
}) {
  const empty = total === 0;
  return (
    <div className="rounded-lg border border-border bg-canvas p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
          {label}
        </span>
        <span className="text-sm font-semibold text-ink">
          {empty ? "—" : `${pct}%`}
        </span>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-border">
        <div
          className={`h-full ${barColor} transition-all`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-ink-muted">
        <span>
          {with_} / {total} have a photo
        </span>
        {!empty && pct < 80 && (
          <span className="text-warning-700">target ≥ 80%</span>
        )}
      </div>
    </div>
  );
}
