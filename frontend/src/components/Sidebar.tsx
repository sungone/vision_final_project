import type { LucideIcon } from 'lucide-react'
import {
  History,
  LayoutDashboard,
  MonitorPlay,
  ScanLine,
  Settings,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import type { SystemStatus } from '../types/vision'

type SidebarProps = {
  mobile?: boolean
  onNavigate?: () => void
  systemStatus?: SystemStatus | null
  statusError?: boolean
}

const navigation: {
  name: string
  path: string
  icon: LucideIcon
}[] = [
  {
    name: '대시보드',
    path: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: '이미지 검사',
    path: '/inspection',
    icon: ScanLine,
  },
  {
    name: '실시간 영상 검사',
    path: '/realtime',
    icon: MonitorPlay,
  },
  {
    name: '검사 이력',
    path: '/history',
    icon: History,
  },
  {
    name: '환경 설정',
    path: '/settings',
    icon: Settings,
  },
]

export default function Sidebar({
  mobile = false,
  onNavigate,
  systemStatus = null,
  statusError = false,
}: SidebarProps) {
  const positionClass = mobile
    ? 'relative flex h-full w-[280px]'
    : 'fixed inset-y-0 left-0 hidden w-[250px] lg:flex'

  const status = getStatusPresentation(
    systemStatus,
    statusError,
  )

  return (
    <aside
      className={`${positionClass} z-50 flex-col bg-[#002c5f] px-4 py-6 text-white`}
    >
      <div className="flex items-center gap-3 px-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-300 bg-[#00a9ce]">
          <ScanLine size={24} />
        </div>

        <div>
          <p className="text-xl font-bold">
            Smart Bolt
          </p>
          <p className="text-xs text-blue-100">
            Vision Program
          </p>
        </div>
      </div>

      <nav className="mt-12 space-y-2">
        {navigation.map(
          ({ name, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              onClick={onNavigate}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold transition',
                  isActive
                    ? 'border border-blue-400/40 bg-[#0b477b] text-white'
                    : 'text-blue-100 hover:bg-white/10 hover:text-white',
                ].join(' ')
              }
            >
              <Icon size={19} />
              {name}
            </NavLink>
          ),
        )}
      </nav>

      <div className="mt-auto border-t border-blue-300/20 px-3 pt-5">
        <div className="flex items-center gap-3">
          <span
            className={`h-3 w-3 shrink-0 rounded-full ${status.dotClass}`}
          />

          <div className="min-w-0">
            <p className="text-sm font-semibold">
              시스템 상태
            </p>

            <p
              className={`mt-0.5 truncate text-xs ${status.textClass}`}
              title={status.label}
            >
              {status.label}
            </p>
          </div>
        </div>
      </div>
    </aside>
  )
}

function getStatusPresentation(
  systemStatus: SystemStatus | null,
  statusError: boolean,
) {
  if (!systemStatus && statusError) {
    return {
      label: '서버 연결 실패',
      dotClass: 'bg-red-400',
      textClass: 'text-red-200',
    }
  }

  if (!systemStatus) {
    return {
      label: '상태 확인 중',
      dotClass:
        'animate-pulse bg-slate-400',
      textClass: 'text-blue-100',
    }
  }

  if (statusError) {
    return {
      label: '상태 갱신 지연',
      dotClass: 'bg-amber-400',
      textClass: 'text-amber-200',
    }
  }

  if (!systemStatus.cameraConnected) {
    return {
      label: '카메라 연결 안 됨',
      dotClass: 'bg-red-400',
      textClass: 'text-red-200',
    }
  }

  if (!systemStatus.modelLoaded) {
    return {
      label: '검사 모델 준비 안 됨',
      dotClass: 'bg-red-400',
      textClass: 'text-red-200',
    }
  }

  if (!systemStatus.visionWorkerRunning) {
    return {
      label: '분석 작업 중지',
      dotClass: 'bg-red-400',
      textClass: 'text-red-200',
    }
  }

  if (!systemStatus.databaseConnected) {
    return {
      label: 'DB 연결 안 됨',
      dotClass: 'bg-amber-400',
      textClass: 'text-amber-200',
    }
  }

  if (
    !systemStatus.persistenceWorkerRunning
  ) {
    return {
      label: '저장 작업 중지',
      dotClass: 'bg-amber-400',
      textClass: 'text-amber-200',
    }
  }

  return {
    label: '모든 서비스 정상',
    dotClass:
      'animate-pulse bg-emerald-400',
    textClass: 'text-emerald-200',
  }
}