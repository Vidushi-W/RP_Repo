import { AudioLines, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { mainNav } from '@/lib/nav'

export function MobileNav() {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-b border-border bg-surface px-4 py-3 md:hidden">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent text-xs font-bold text-accent-foreground"><AudioLines size={18} /></div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-accent">SLSL AI Studio</p>
            <p className="text-xs text-muted">Motion into meaning</p>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-controls="mobile-workspace-navigation" aria-label={open ? 'Close navigation' : 'Open navigation'}>
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
      </div>
      {open && (
        <nav id="mobile-workspace-navigation" aria-label="Mobile navigation" className="mt-3 grid gap-1 rounded-lg border border-border bg-surface-muted p-2">
          {mainNav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium',
                  isActive ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-surface hover:text-foreground',
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}
