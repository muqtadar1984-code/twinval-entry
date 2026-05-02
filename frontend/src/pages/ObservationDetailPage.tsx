import { ArrowLeft, CheckCircle2, ShieldAlert, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { EntryRefId } from "../components/EntryRefId";
import { HashDisplay } from "../components/HashDisplay";
import { InlineSpinner, LoadingState } from "../components/LoadingState";
import { SeverityBadge } from "../components/SeverityBadge";
import { useAuth } from "../contexts/AuthContext";
import { admin as adminApi, observations as obsApi } from "../lib/api";
import { formatDate } from "../lib/format";
import type { Observation, ObservationVerifyResult } from "../types/api";
import { STREAM_LABELS } from "../types/api";

export function ObservationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [entry, setEntry] = useState<Observation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [verifying, setVerifying] = useState(false);
  const [verification, setVerification] = useState<ObservationVerifyResult | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const [reviewing, setReviewing] = useState(false);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    obsApi
      .get(id)
      .then((e) => setEntry(e))
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load observation."));
  }, [id]);

  async function onVerify() {
    if (!id) return;
    setVerifying(true);
    setVerifyError(null);
    try {
      const result = await obsApi.verify(id);
      setVerification(result);
    } catch (e: any) {
      setVerifyError(e?.response?.data?.detail || "Verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  async function onMarkReviewed() {
    if (!id) return;
    setReviewing(true);
    setReviewError(null);
    try {
      const updated = await adminApi.review(id, reviewNote || null);
      setEntry(updated);
      setReviewNote("");
    } catch (e: any) {
      setReviewError(e?.response?.data?.detail || "Could not mark as reviewed.");
    } finally {
      setReviewing(false);
    }
  }

  if (error) {
    return (
      <div className="card p-6 text-sm text-danger-700">{error}</div>
    );
  }
  if (!entry) {
    return <LoadingState />;
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Link
        to="/history"
        className="mb-4 inline-flex items-center gap-1 text-sm text-ink-muted hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </Link>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <EntryRefId refId={entry.entry_ref_id} copyable />
          <SeverityBadge severity={entry.severity} />
          <span className="pill border border-border bg-canvas text-ink-muted">
            chain #{entry.chain_sequence}
          </span>
          {entry.reviewed && (
            <span className="pill border border-accent/30 bg-accent-50 text-accent-700">
              <CheckCircle2 className="h-3 w-3" /> reviewed
            </span>
          )}
        </div>
      </div>

      {/* Photo */}
      {entry.photo_url && !entry.photo_url.startsWith("local-stub://") && (
        <div className="card mb-4 overflow-hidden">
          <img
            src={entry.photo_url}
            alt="Observation photo"
            className="w-full max-h-96 object-cover"
          />
        </div>
      )}

      {/* Description */}
      <div className="card p-5">
        <h2 className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
          Description
        </h2>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink">
          {entry.description}
        </p>
      </div>

      {/* Metadata */}
      <div className="card mt-4 divide-y divide-border">
        <DetailRow label="Property">
          <div className="font-medium text-ink">{entry.property_name}</div>
          <div className="text-xs text-ink-subtle">
            {entry.building_label} · {entry.zone_label}
          </div>
        </DetailRow>
        <DetailRow label="Owner / Stream">
          <div className="text-ink">{entry.owner_profile_name}</div>
          <div className="text-xs text-ink-subtle">{STREAM_LABELS[entry.stream]}</div>
        </DetailRow>
        <DetailRow label="Type">{entry.observation_type}</DetailRow>
        <DetailRow label="Submitted">{formatDate(entry.submitted_at)}</DetailRow>
      </div>

      {/* Hash chain */}
      <div className="card mt-4 p-5">
        <h2 className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
          Hash Chain
        </h2>
        <dl className="mt-3 space-y-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Entry hash</dt>
            <dd>
              <HashDisplay hash={entry.entry_hash} />
            </dd>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <dt className="text-ink-muted">Previous hash</dt>
            <dd>
              <HashDisplay hash={entry.prev_hash} />
            </dd>
          </div>
        </dl>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={onVerify}
            disabled={verifying}
            className="btn-secondary"
          >
            {verifying ? <InlineSpinner /> : <ShieldCheck className="h-4 w-4" />}
            Verify integrity
          </button>
          {verification && <VerificationResult result={verification} />}
          {verifyError && <span className="text-xs text-danger">{verifyError}</span>}
        </div>
      </div>

      {/* Admin review */}
      {user?.role === "admin" && (
        <div className="card mt-4 p-5">
          <h2 className="text-xs font-medium uppercase tracking-wide text-ink-subtle">
            Admin review
          </h2>
          {entry.reviewed ? (
            <div className="mt-3 text-sm">
              <div className="flex items-center gap-2 text-accent-700">
                <CheckCircle2 className="h-4 w-4" />
                Reviewed on {formatDate(entry.reviewed_at)}
              </div>
              {entry.reviewer_note && (
                <p className="mt-2 whitespace-pre-wrap text-ink">
                  {entry.reviewer_note}
                </p>
              )}
            </div>
          ) : (
            <div className="mt-3 space-y-3">
              <textarea
                rows={3}
                className="input"
                placeholder="Optional review note…"
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
              />
              {reviewError && <p className="text-xs text-danger">{reviewError}</p>}
              <button
                type="button"
                onClick={onMarkReviewed}
                disabled={reviewing}
                className="btn-primary"
              >
                {reviewing ? <InlineSpinner /> : "Mark as reviewed"}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 px-5 py-3">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="text-right text-sm text-ink">{children}</dd>
    </div>
  );
}

function VerificationResult({ result }: { result: ObservationVerifyResult }) {
  const allOk = result.valid && result.chain_intact;
  if (allOk) {
    return (
      <div className="inline-flex items-center gap-2 rounded-lg bg-accent-50 px-3 py-1.5 text-xs font-medium text-accent-700">
        <ShieldCheck className="h-4 w-4" />
        Hash matches and chain intact.
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-2 rounded-lg bg-danger-50 px-3 py-1.5 text-xs font-medium text-danger-700">
      <ShieldAlert className="h-4 w-4" />
      {!result.valid && "Hash mismatch. "}
      {!result.chain_intact && "Chain link broken."}
    </div>
  );
}
