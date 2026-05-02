import { Play, ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { InlineSpinner } from "../../components/LoadingState";
import { admin as adminApi } from "../../lib/api";
import type { ChainAuditResult } from "../../types/api";

export function AdminChainAuditTab() {
  const [result, setResult] = useState<ChainAuditResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ranAt, setRanAt] = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const r = await adminApi.chainVerify();
      setResult(r);
      setRanAt(new Date().toISOString());
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Chain verification failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink">Full chain verification</h2>
        <p className="mt-1 text-sm text-ink-muted">
          Walks every entry in chain order, recomputes each entry's SHA-256 hash, and checks
          linkage against the previous entry. Tampered or broken records are flagged here.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button type="button" onClick={run} disabled={running} className="btn-primary">
            {running ? <InlineSpinner /> : <Play className="h-4 w-4" />}
            {running ? "Running…" : "Run verification"}
          </button>
          {ranAt && !running && (
            <span className="text-xs text-ink-muted">
              Last run: {new Date(ranAt).toLocaleTimeString()}
            </span>
          )}
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
        )}

        {result && (
          <div className="mt-6 space-y-4">
            <div
              className={`flex items-start gap-3 rounded-lg p-4 ${
                result.chain_valid
                  ? "bg-accent-50 text-accent-700"
                  : "bg-danger-50 text-danger-700"
              }`}
            >
              {result.chain_valid ? (
                <ShieldCheck className="mt-0.5 h-5 w-5 flex-shrink-0" />
              ) : (
                <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0" />
              )}
              <div>
                <div className="text-sm font-semibold">
                  {result.chain_valid ? "Chain is intact" : "Chain integrity compromised"}
                </div>
                <div className="mt-0.5 text-sm">
                  {result.total_entries} entries audited.
                  {!result.chain_valid &&
                    ` ${result.broken_links.length} broken link${
                      result.broken_links.length === 1 ? "" : "s"
                    }.`}
                </div>
              </div>
            </div>

            {!result.chain_valid && result.broken_links.length > 0 && (
              <div className="card border-danger/30 p-4">
                <h3 className="text-sm font-semibold text-danger-700">Broken entries</h3>
                <ul className="mt-2 space-y-1 text-sm">
                  {result.broken_links.map((ref) => (
                    <li key={ref} className="mono text-danger-700">
                      {ref}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-xs text-ink-muted">
                  Inspect these entries individually via{" "}
                  <Link to="/admin" className="underline">
                    All Observations
                  </Link>{" "}
                  and reconcile with database backups.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
