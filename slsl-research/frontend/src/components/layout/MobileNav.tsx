import { Menu } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const links = [
  ['/', 'Overview'],
  ['/datasets', 'Datasets'],
  ['/training', 'Training'],
  ['/evaluation', 'Evaluation'],
  ['/playground', 'Playground'],
] as const

export function MobileNav() {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-b border-[var(--color-border)] bg-white px-4 py-3 md:hidden">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-600">SLSL AI Studio</p>
          <p className="text-sm font-semibold">Continuous Sign Research</p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setOpen((v) => !v)} aria-label="Open navigation">
          <Menu className="h-4 w-4" />
        </Button>
      </div>
      {open && (
        <nav className="mt-3 grid gap-1">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn('rounded-md px-3 py-2 text-sm', isActive ? 'bg-indigo-50 text-indigo-700' : 'text-[var(--color-muted)]')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}
