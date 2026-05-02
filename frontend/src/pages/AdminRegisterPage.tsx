import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { InlineSpinner } from "../components/LoadingState";
import { admin as adminApi } from "../lib/api";
import type { UserRole } from "../types/api";

const ROLES: { id: UserRole; label: string; description: string }[] = [
  { id: "intern", label: "Intern", description: "Captures observations and enrols properties." },
  { id: "stakeholder", label: "Stakeholder", description: "REIT/lender/owner — read-only via grants." },
  { id: "auditor", label: "Auditor", description: "Read-only across all observations." },
  { id: "admin", label: "Admin", description: "Full access. Issue with care." },
];

export function AdminRegisterPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("intern");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ name: string; email: string } | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await adminApi.registerUser({ name, email, password, role });
      setCreated({ name: u.name, email: u.email });
      setName("");
      setEmail("");
      setPassword("");
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 409) setError("That email is already registered.");
      else setError(e?.response?.data?.detail || "Could not create user.");
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <div className="mx-auto max-w-md">
        <div className="card p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-6 w-6 text-accent" />
            <div>
              <h2 className="text-lg font-semibold text-ink">User created</h2>
              <p className="mt-1 text-sm text-ink-muted">
                {created.name} ({created.email}) is now registered. Share the credentials securely
                — they should change the password on first sign-in.
              </p>
            </div>
          </div>
          <div className="mt-5 flex gap-2">
            <button
              onClick={() => setCreated(null)}
              className="btn-secondary flex-1 justify-center"
            >
              Register another
            </button>
            <button
              onClick={() => navigate("/admin")}
              className="btn-primary flex-1 justify-center"
            >
              Back to admin
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <Link
        to="/admin"
        className="mb-4 inline-flex items-center gap-1 text-sm text-ink-muted hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" /> Back to admin
      </Link>

      <div className="card p-6">
        <h1 className="text-lg font-semibold text-ink">Register user</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Create a new account. The user will sign in with these credentials.
        </p>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          <div>
            <label htmlFor="name" className="label">Full name</label>
            <input
              id="name"
              className="input"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={busy}
            />
          </div>
          <div>
            <label htmlFor="email" className="label">Email</label>
            <input
              id="email"
              type="email"
              className="input"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
            />
          </div>
          <div>
            <label htmlFor="password" className="label">Temporary password</label>
            <input
              id="password"
              type="text"
              className="input mono"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={busy}
            />
            <p className="mt-1 text-xs text-ink-subtle">
              Min 8 characters. The user should change this on first sign-in.
            </p>
          </div>
          <div>
            <label className="label">Role</label>
            <div className="space-y-2">
              {ROLES.map((r) => (
                <label
                  key={r.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${
                    role === r.id
                      ? "border-primary bg-primary-50"
                      : "border-border bg-surface hover:border-primary/40"
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={r.id}
                    checked={role === r.id}
                    onChange={() => setRole(r.id)}
                    className="mt-1"
                  />
                  <div>
                    <div className="text-sm font-medium text-ink">{r.label}</div>
                    <div className="text-xs text-ink-muted">{r.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {error && (
            <div className="rounded-lg bg-danger-50 p-3 text-sm text-danger-700">{error}</div>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? <InlineSpinner /> : "Register user"}
          </button>
        </form>
      </div>
    </div>
  );
}
