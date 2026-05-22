import { Navigate, Route, Routes, useSearchParams } from "react-router-dom";

import { DashboardLayout } from "./layouts/DashboardLayout";
import { AuthPage } from "./pages/AuthPage";
import { EvaluatePage } from "./pages/EvaluatePage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProfileSetupPage } from "./pages/ProfileSetupPage";
import { ReportsPage } from "./pages/ReportsPage";

function RegisterToLogin() {
  const [sp] = useSearchParams();
  const next = sp.get("next");
  const q = new URLSearchParams();
  q.set("mode", "register");
  if (next?.startsWith("/")) q.set("next", next);
  return <Navigate to={`/login?${q.toString()}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage />} />
      <Route path="/register" element={<RegisterToLogin />} />
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<Navigate to="/evaluate" replace />} />
        <Route path="/evaluate" element={<EvaluatePage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/profile/setup" element={<ProfileSetupPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/evaluate" replace />} />
    </Routes>
  );
}

