import { NavLink } from 'react-router-dom'
import { Activity, ArrowUpRight, AudioLines, CircleHelp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { mainNav } from '@/lib/nav'
import { useHealth } from '@/hooks/useSystemStatus'

export function Sidebar() {
  const { data: health } = useHealth()
  return <aside className="studio-sidebar hidden md:flex">
    <NavLink to="/" className="studio-brand"><span className="brand-mark"><AudioLines size={23} /></span><div><span className="block text-base font-semibold tracking-tight">SLSL<span className="font-normal opacity-70"> studio</span></span><span className="mt-1 block text-[10px] tracking-[.2em] opacity-50">MOTION INTO MEANING</span></div></NavLink>
    <div className="mx-5 mt-4 rounded-xl border border-white/10 bg-white/5 px-3.5 py-3"><div className="flex items-center gap-2 text-xs"><span className="h-1.5 w-1.5 rounded-full bg-[#a9d9bb]" />Research workspace</div><p className="mt-1.5 pl-3.5 text-[11px] text-white/45">Local · Single model</p></div>
    <p className="mb-3 mt-9 px-7 text-[10px] font-medium tracking-[.18em] text-white/35">WORKSPACE</p>
    <nav aria-label="Main navigation" className="space-y-1 px-4">{mainNav.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => cn('sidebar-link', isActive && 'is-active')}><Icon size={18} strokeWidth={1.7} /><span className="flex-1">{label}</span><ArrowUpRight size={14} className="nav-arrow" /></NavLink>)}</nav>
    <div className="mx-5 mb-5 mt-auto rounded-xl border border-white/10 p-4"><CircleHelp size={18} className="text-[#b5d7c6]" /><p className="mt-3 text-xs font-medium">One step at a time.</p><p className="mt-2 text-[11px] leading-5 text-white/50">Add your recordings, train your model, then test what it knows.</p><NavLink to="/datasets" className="mt-3 inline-flex items-center gap-2 text-xs text-[#b5d7c6]">Manage recordings <ArrowUpRight size={13} /></NavLink></div>
    <div className="flex items-center gap-2 border-t border-white/10 px-6 py-5 text-[11px] text-white/55"><Activity size={14} /><span className={`h-1.5 w-1.5 rounded-full ${health?.status === 'ok' ? 'bg-[#a9d9bb]' : 'bg-amber-300'}`} />{health?.status === 'ok' ? 'System connected' : 'Backend unavailable'}</div>
  </aside>
}
