import { Outlet, useLocation } from 'react-router-dom'
import { PanelLeft, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { PageContainer } from '@/components/layout/PageContainer'
import { WorkspaceDialog } from '@/features/studio/StudioWidgets'
import { Button } from '@/components/ui/button'
import { mainNav } from '@/lib/nav'
import { MobileNav } from './MobileNav'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const location = useLocation()
  const qc = useQueryClient()
  const page = mainNav.find(item => item.to === location.pathname)?.label || 'Overview'
  return <div className="flex min-h-screen app-shell-bg"><Sidebar /><div className="min-w-0 flex-1">
    <MobileNav />
    <div className="studio-topbar"><div className="flex items-center gap-3 text-xs"><PanelLeft size={15} className="text-muted" /><span className="hidden text-muted sm:inline">Workspace</span><span className="text-border-strong">/</span><span className="font-medium">{page}</span></div><div className="flex items-center gap-2"><span className="local-badge hidden lg:inline-flex">LOCAL STUDIO</span><Button variant="ghost" size="sm" aria-label="Refresh dashboard" onClick={() => { void qc.invalidateQueries() }}><RefreshCw className="h-3.5 w-3.5" /></Button><WorkspaceDialog /><span className="workspace-avatar" aria-label="Research workspace">SL</span></div></div>
    <main className="px-4 py-7 md:px-8 lg:px-10 lg:py-9"><PageContainer><Outlet /></PageContainer></main>
  </div></div>
}
