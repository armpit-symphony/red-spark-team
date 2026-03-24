import { Routes, Route, Navigate } from 'react-router-dom';

import { AppShell } from './components/layout/AppShell';
import { AppToaster } from './components/ui/sonner';
import OverviewPage from './pages/OverviewPage';
import TargetsPage from './pages/TargetsPage';
import PoliciesPage from './pages/PoliciesPage';
import AuditRunsPage from './pages/AuditRunsPage';
import RunDetailPage from './pages/RunDetailPage';
import FindingsPage from './pages/FindingsPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import AuditLogPage from './pages/AuditLogPage';

export default function App() {
  return (
    <>
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/targets" element={<TargetsPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/audit-runs" element={<AuditRunsPage />} />
          <Route path="/audit-runs/:runId" element={<RunDetailPage />} />
          <Route path="/findings" element={<FindingsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/audit-log" element={<AuditLogPage />} />
        </Routes>
      </AppShell>
      <AppToaster />
    </>
  );
}
