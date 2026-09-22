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
import PlaceholderPage from './pages/PlaceholderPage'

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
            path="/history"
            element={<HistoryPage />}
          />

          <Route
            path="/history/:inspectionId"
            element={<InspectionDetailPage />}
          />

          <Route
            path="/settings"
            element={
              <PlaceholderPage
                title="환경 설정"
                description="검사 기준과 시스템 상태를 확인합니다."
              />
            }
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