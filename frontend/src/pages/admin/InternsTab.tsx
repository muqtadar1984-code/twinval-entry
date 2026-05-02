import { UserPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { LoadingState } from "../../components/LoadingState";
import { admin as adminApi } from "../../lib/api";
import { formatDateShort } from "../../lib/format";
import type { User } from "../../types/api";

export function AdminInternsTab() {
  const [items, setItems] = useState<User[] | null>(null);

  useEffect(() => {
    adminApi
      .listUsers({ limit: 200 })
      .then((p) => setItems(p.items))
      .catch(() => setItems([]));
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-ink">Users</h2>
        <Link to="/admin/register" className="btn-primary">
          <UserPlus className="h-4 w-4" /> Register user
        </Link>
      </div>

      {items === null ? (
        <LoadingState />
      ) : items.length === 0 ? (
        <div className="card p-8 text-center text-sm text-ink-muted">No users registered.</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="bg-canvas">
              <tr className="text-left text-xs font-medium uppercase tracking-wide text-ink-subtle">
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Email</th>
                <th className="px-5 py-3">Role</th>
                <th className="px-5 py-3">Joined</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((u) => (
                <tr key={u.id} className="text-sm">
                  <td className="px-5 py-3 font-medium text-ink">{u.name}</td>
                  <td className="px-5 py-3 text-ink-muted">{u.email}</td>
                  <td className="px-5 py-3">
                    <span
                      className={`pill capitalize ${
                        u.role === "admin"
                          ? "bg-primary-50 text-primary"
                          : u.role === "stakeholder"
                          ? "bg-warning-50 text-warning-700"
                          : u.role === "auditor"
                          ? "bg-canvas text-ink-muted border border-border"
                          : "bg-accent-50 text-accent-700"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-ink-muted">{formatDateShort(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
