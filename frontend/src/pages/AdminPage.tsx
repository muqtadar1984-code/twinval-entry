import { useState } from "react";

import { AdminChainAuditTab } from "./admin/ChainAuditTab";
import { AdminConfigurationTab } from "./admin/ConfigurationTab";
import { AdminInternsTab } from "./admin/InternsTab";
import { AdminObservationsTab } from "./admin/ObservationsTab";
import { PropertiesAnalyticsTab } from "./admin/PropertiesAnalyticsTab";

type Tab = "properties" | "observations" | "audit" | "config" | "interns";

const TABS: { id: Tab; label: string }[] = [
  { id: "properties", label: "Properties" },
  { id: "observations", label: "All Observations" },
  { id: "audit", label: "Chain Audit" },
  { id: "config", label: "Configuration" },
  { id: "interns", label: "Users" },
];

export function AdminPage() {
  const [tab, setTab] = useState<Tab>("properties");

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-ink">Admin</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Review observations, audit the chain, and manage portal configuration.
        </p>
      </div>

      <div className="mb-5 overflow-x-auto border-b border-border">
        <nav className="-mb-px flex gap-1">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id)}
                className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition ${
                  active
                    ? "border-primary text-primary"
                    : "border-transparent text-ink-muted hover:text-ink"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </nav>
      </div>

      {tab === "properties" && <PropertiesAnalyticsTab />}
      {tab === "observations" && <AdminObservationsTab />}
      {tab === "audit" && <AdminChainAuditTab />}
      {tab === "config" && <AdminConfigurationTab />}
      {tab === "interns" && <AdminInternsTab />}
    </div>
  );
}
