import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string
  hint?: string
  icon?: LucideIcon
  tone?: 'default' | 'accent' | 'success' | 'warning'
  className?: string
}

const toneStyles = {
  default: 'bg-surface',
  accent: 'bg-accent-soft border-accent/15',
  success: 'bg-success-soft border-emerald-200/60',
  warning: 'bg-warning-soft border-amber-200/60',
}

const iconStyles = {
  default: 'bg-surface-muted text-muted',
  accent: 'bg-accent/10 text-accent',
  success: 'bg-emerald-100 text-success',
  warning: 'bg-amber-100 text-warning',
}

export function StatCard({ label, value, hint, icon: Icon, tone = 'default', className }: StatCardProps) {
  return (
    <div className={cn('rounded-xl border border-border p-4 shadow-sm', toneStyles[tone], className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
          <p className="mt-1 truncate text-2xl font-semibold tracking-tight text-foreground">{value}</p>
          {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
        </div>
        {Icon && (
          <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', iconStyles[tone])}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
    </div>
  )
}
