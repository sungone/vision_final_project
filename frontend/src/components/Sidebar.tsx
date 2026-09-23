import type { LucideIcon } from 'lucide-react'
import {
  History,
  LayoutDashboard,
  ScanLine,
  Settings,
  Video,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

type SidebarProps = {
  mobile?: boolean
  onNavigate?: () => void
}

const navigation: {
  name: string
  path: string
  icon: LucideIcon
}[] = [
  { name: '대시보드', path: '/dashboard', icon: LayoutDashboard },
  { name: '실시간 검사', path: '/realtime', icon: Video,},
  { name: '이미지 검사', path: '/inspection', icon: ScanLine },
  { name: '검사 이력', path: '/history', icon: History },
  { name: '환경 설정', path: '/settings', icon: Settings },
]

export default function Sidebar({
  mobile = false,
  onNavigate,
}: SidebarProps) {
  const positionClass = mobile
    ? 'relative flex h-full w-[280px]'
    : 'fixed inset-y-0 left-0 hidden w-[250px] lg:flex'

  return (
    <aside
      className={`${positionClass} z-50 flex-col bg-[#002c5f] px-4 py-6 text-white`}
    >
      <div className="flex items-center gap-3 px-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-300 bg-[#00a9ce]">
          <ScanLine size={24} />
        </div>

        <div>
          <p className="text-xl font-bold">Smart Bolt</p>
          <p className="text-xs text-blue-100">Vision Program</p>
        </div>
      </div>

      <nav className="mt-12 space-y-2">
        {navigation.map(({ name, path, icon: Icon }) => (
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
        ))}
      </nav>

      <div className="mt-auto border-t border-blue-300/20 px-3 pt-5">
        <div className="flex items-center gap-3">
          <span className="h-3 w-3 rounded-full bg-emerald-400" />

          <div>
            <p className="text-sm font-semibold">시스템 상태</p>
            <p className="text-xs text-blue-100">모든 서비스 정상</p>
          </div>
        </div>
      </div>
    </aside>
  )
}