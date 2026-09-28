import {
  Menu,
  ScanLine,
  X,
} from 'lucide-react'
import {
  useEffect,
  useState,
} from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { getSystemStatus } from '../services/inspectionApi'
import type { SystemStatus } from '../types/vision'

export default function AppLayout() {
  const [menuOpen, setMenuOpen] =
    useState(false)

  const [systemStatus, setSystemStatus] =
    useState<SystemStatus | null>(null)

  const [statusError, setStatusError] =
    useState(false)

  useEffect(() => {
    let disposed = false
    let requestInFlight = false
    const controller = new AbortController()

    async function refreshStatus() {
      if (requestInFlight) {
        return
      }

      requestInFlight = true

      try {
        const result = await getSystemStatus(
          controller.signal,
        )

        if (!disposed) {
          setSystemStatus(result)
          setStatusError(false)
        }
      } catch {
        if (
          !disposed &&
          !controller.signal.aborted
        ) {
          setStatusError(true)
        }
      } finally {
        requestInFlight = false
      }
    }

    void refreshStatus()

    const timer = window.setInterval(() => {
      void refreshStatus()
    }, 5000)

    return () => {
      disposed = true
      window.clearInterval(timer)
      controller.abort()
    }
  }, [])

  return (
    <div className="min-h-screen bg-[#f4f7fa]">
      <Sidebar
        systemStatus={systemStatus}
        statusError={statusError}
      />

      <header className="sticky top-0 z-40 flex h-[72px] items-center justify-between bg-[#002c5f] px-5 text-white lg:hidden">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#00a9ce]">
            <ScanLine size={22} />
          </div>

          <div>
            <p className="font-bold">
              Smart Bolt
            </p>
            <p className="text-[11px] text-blue-100">
              Vision Program
            </p>
          </div>
        </div>

        <button
          type="button"
          aria-label="메뉴 열기"
          onClick={() => setMenuOpen(true)}
          className="rounded-lg p-2 hover:bg-white/10"
        >
          <Menu />
        </button>
      </header>

      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="메뉴 닫기"
            className="absolute inset-0 bg-black/45"
            onClick={() =>
              setMenuOpen(false)
            }
          />

          <div className="relative h-full w-[280px]">
            <Sidebar
              mobile
              systemStatus={systemStatus}
              statusError={statusError}
              onNavigate={() =>
                setMenuOpen(false)
              }
            />

            <button
              type="button"
              aria-label="메뉴 닫기"
              onClick={() =>
                setMenuOpen(false)
              }
              className="absolute right-4 top-5 rounded-lg p-2 text-white hover:bg-white/10"
            >
              <X size={22} />
            </button>
          </div>
        </div>
      )}

      <main className="min-h-screen lg:pl-[250px]">
        <Outlet />
      </main>
    </div>
  )
}