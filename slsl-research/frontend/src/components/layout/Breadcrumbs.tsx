import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

export interface BreadcrumbItem {
  label: string
  href?: string
}

export function Breadcrumbs({ items, className }: { items: BreadcrumbItem[]; className?: string }) {
  if (!items.length) return null
  return (
    <nav aria-label="Breadcrumb" className={cn('mb-3 flex flex-wrap items-center gap-1 text-xs text-muted', className)}>
      {items.map((item, i) => (
        <span key={`${item.label}-${i}`} className="inline-flex items-center gap-1">
          {i > 0 && <ChevronRight className="h-3 w-3 opacity-50" />}
          {item.href ? (
            <Link to={item.href} className="font-medium text-accent hover:underline">{item.label}</Link>
          ) : (
            <span className="font-medium text-foreground">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
