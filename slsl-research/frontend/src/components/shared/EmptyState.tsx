import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  className?: string
  action?: React.ReactNode
}

export function EmptyState({ icon: Icon, title, description, className, action }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center rounded-xl border border-dashed border-[var(--color-border)] bg-white px-6 py-12 text-center', className)}>
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-base font-semibold text-[var(--color-foreground)]">{title}</h3>
      <p className="mt-2 max-w-md text-sm leading-6 text-[var(--color-muted)]">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
