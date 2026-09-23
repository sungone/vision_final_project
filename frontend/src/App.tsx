import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import DashboardPage from './pages/DashboardPage'
import HistoryPage from './pages/HistoryPage'
import InspectionDetailPage from './pages/InspectionDetailPage'
import InspectionPage from './pages/InspectionPage'
import SettingsPage from './pages/SettingsPage'
import RealtimeInspectionPage from './pages/RealtimeInspectionPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Navigate to="/dashboard" replace />
            }
          />

          <Route
            path="/dashboard"
            element={<DashboardPage />}
          />

          <Route
            path="/inspection"
            element={<InspectionPage />}
          />

          <Route
            path="/realtime"
            element={<RealtimeInspectionPage />}
          />

          <Route
            path="/history"
            element={<HistoryPage />}
          />

          <Route
            path="/history/:inspectionId"
            element={<InspectionDetailPage />}
          />

          <Route
            path="/settings"
            element={<SettingsPage />}
          />

          <Route
            path="*"
            element={
              <Navigate to="/dashboard" replace />
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}