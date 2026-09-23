import { Navigate, Route, Routes } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import AuthPage from './pages/AuthPage';
import VerifyPage from './pages/VerifyPage';
import OverviewPage from './pages/OverviewPage';
import TicketsPage from './pages/TicketsPage';
import CreateTicketPage from './pages/CreateTicketPage';
import TicketDetailsPage from './pages/TicketDetailsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';

const isAuthenticated = () => Boolean(localStorage.getItem('datastraw_session_token'));

function App() {
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated() ? <Navigate to="/overview" replace /> : <AuthPage />} />
      <Route path="/verify" element={isAuthenticated() ? <Navigate to="/overview" replace /> : <VerifyPage />} />

      <Route element={<DashboardLayout />}>
        <Route path="/overview" element={isAuthenticated() ? <OverviewPage /> : <Navigate to="/login" replace />} />
        <Route path="/tickets" element={isAuthenticated() ? <TicketsPage /> : <Navigate to="/login" replace />} />
        <Route path="/tickets/new" element={isAuthenticated() ? <CreateTicketPage /> : <Navigate to="/login" replace />} />
        <Route path="/tickets/:ticketId" element={isAuthenticated() ? <TicketDetailsPage /> : <Navigate to="/login" replace />} />
        <Route path="/analytics" element={isAuthenticated() ? <AnalyticsPage /> : <Navigate to="/login" replace />} />
        <Route path="/settings" element={isAuthenticated() ? <SettingsPage /> : <Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to={isAuthenticated() ? '/overview' : '/login'} replace />} />
      </Route>
    </Routes>
  );
}

export default App;
