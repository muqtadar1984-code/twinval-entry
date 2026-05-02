import { AlertCircle } from "lucide-react";
import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { HashChainIcon } from "../components/HashChainIcon";
import { InlineSpinner } from "../components/LoadingState";
import { useAuth } from "../contexts/AuthContext";

interface LocationState {
  from?: string;
}

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!loading && user) {
    const dest = (location.state as LocationState)?.from || "/dashboard";
    return <Navigate to={dest} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      const dest = (location.state as LocationState)?.from || "/dashboard";
      navigate(dest, { replace: true });
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 401) setError("Email or password is incorrect.");
      else if (status === 429)
        setError("Too many login attempts. Please wait a few minutes and try again.");
      else setError("Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas px-4 py-10 sm:py-16">
      <div className="mx-auto max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="flex items-center gap-2 text-primary">
            <HashChainIcon className="h-8 w-8" />
            <h1 className="text-xl font-semibold">TwinVal</h1>
          </div>
          <p className="mt-1 text-sm text-ink-muted">Field Observation System</p>
        </div>

        <div className="card p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-ink">Sign in</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Enter your credentials to access the portal.
          </p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div>
              <label htmlFor="email" className="label">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
              />
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg bg-danger-50 p-3 text-sm text-danger-700">
                <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full"
              disabled={submitting || !email || !password}
            >
              {submitting ? (
                <>
                  <InlineSpinner /> Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-ink-subtle">
          Forgot your password? Contact your TwinVal administrator.
        </p>
      </div>
    </div>
  );
}
