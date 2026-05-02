import { LogOut, Menu, X } from "lucide-react";
import { ReactNode, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import { HashChainIcon } from "./HashChainIcon";

interface Props {
  children: ReactNode;
}

export function Layout({ children }: Props) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function onLogout() {
    await logout();
    navigate("/login");
  }

  const navItems = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/submit", label: "New Observation" },
    { to: "/history", label: "History" },
  ];
  if (user?.role === "admin") {
    navItems.push({ to: "/admin", label: "Admin" });
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-30 border-b border-border bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/dashboard" className="flex items-center gap-2 text-primary">
            <HashChainIcon className="h-6 w-6" />
            <div>
              <div className="text-sm font-semibold leading-tight">TwinVal</div>
              <div className="text-[11px] uppercase tracking-wide text-ink-muted leading-tight">
                Field Observation System
              </div>
            </div>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium transition ${
                    isActive
                      ? "bg-primary-50 text-primary"
                      : "text-ink-muted hover:bg-canvas hover:text-ink"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <div className="text-right text-xs">
              <div className="font-medium text-ink">{user?.name}</div>
              <div className="capitalize text-ink-subtle">{user?.role}</div>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-ink-muted hover:bg-canvas hover:text-ink"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>

          <button
            type="button"
            className="rounded p-2 text-ink-muted md:hidden"
            onClick={() => setMobileOpen((s) => !s)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileOpen && (
          <nav className="border-t border-border bg-surface md:hidden">
            <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `rounded-md px-3 py-2 text-sm font-medium ${
                      isActive ? "bg-primary-50 text-primary" : "text-ink"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
              <div className="my-2 border-t border-border" />
              <div className="px-3 text-xs text-ink-muted">
                Signed in as <span className="font-medium text-ink">{user?.name}</span>{" "}
                ({user?.role})
              </div>
              <button
                type="button"
                onClick={onLogout}
                className="mt-2 inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm text-danger hover:bg-danger-50"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
