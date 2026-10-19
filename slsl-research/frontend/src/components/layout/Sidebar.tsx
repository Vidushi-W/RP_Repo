import {
  BarChart3,
  Brain,
  Database,
  LayoutDashboard,
  MessageSquare,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useHealth, useSystemStatus } from '@/hooks/useSystemStatus'
import { SettingsDialog } from './SettingsDialog'

const nav = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/datasets', label: 'Datasets', icon: Database },
  { to: '/training', label: 'Training', icon: Brain },
  { to: '/evaluation', label: 'Evaluation', icon: BarChart3 },
  { to: '/playground', label: 'Playground', icon: MessageSquare },
]

export function Sidebar() {
  const { data: health } = useHealth()
  const { data: status } = useSystemStatus()

  return (
    <aside className="hidden h-screen w-64 shrink-0 flex-col border-r border-[var(--color-border)] bg-white md:flex">
      <div className="border-b border-[var(--color-border)] px-5 py-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-600">SLSL AI Studio</p>
        <h1 className="mt-1 text-base font-semibold text-[var(--color-foreground)]">Continuous Sign Research</h1>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
                isActive ? 'bg-indigo-50 text-indigo-700' : 'text-[var(--color-muted)] hover:bg-slate-50 hover:text-[var(--color-foreground)]',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 pb-2">
        <SettingsDialog />
      </div>

      <div className="border-t border-[var(--color-border)] px-4 py-4 text-xs text-[var(--color-muted)]">
        <div className="flex items-center justify-between">
          <span>Backend</span>
          <Badge variant={health?.status === 'ok' ? 'success' : 'warning'}>
            {health?.status === 'ok' ? 'Online' : 'Offline'}
          </Badge>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <span>Models</span>
          <span className="font-medium text-[var(--color-foreground)]">{status?.model_count ?? 0}</span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <span>Datasets</span>
          <span className="font-medium text-[var(--color-foreground)]">{status?.dataset_count ?? 0}</span>
        </div>
      </div>
    </aside>
  )
}
