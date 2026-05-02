import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminPage } from "./pages/AdminPage";
import { AdminRegisterPage } from "./pages/AdminRegisterPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { ObservationDetailPage } from "./pages/ObservationDetailPage";
import { SubmitPage } from "./pages/SubmitPage";

function NotFoundPage() {
  return (
    <div className="card mx-auto max-w-md p-8 text-center">
      <h1 className="text-lg font-semibold text-ink">Page not found</h1>
      <p className="mt-1 text-sm text-ink-muted">
        That route doesn't exist in the portal.
      </p>
    </div>
  );
}

function withLayout(Page: () => JSX.Element) {
  return (
    <ProtectedRoute>
      <Layout>
        <Page />
      </Layout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />

      <Route path="/dashboard" element={withLayout(DashboardPage)} />
      <Route path="/submit" element={withLayout(SubmitPage)} />
      <Route path="/history" element={withLayout(HistoryPage)} />
      <Route path="/observations/:id" element={withLayout(ObservationDetailPage)} />

      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout>
              <AdminPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/register"
        element={
          <ProtectedRoute allowedRoles={["admin"]}>
            <Layout>
              <AdminRegisterPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={withLayout(NotFoundPage)} />
    </Routes>
  );
}
