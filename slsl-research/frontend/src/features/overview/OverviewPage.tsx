import { Activity, ArrowRight, Brain, CheckCircle2, Circle, Database, Play, Upload } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/layout/PageHeader'
import { LoadingCardGrid } from '@/components/shared/LoadingState'
import { StatCard } from '@/components/shared/StatCard'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealth, useSystemStatus } from '@/hooks/useSystemStatus'

export function OverviewPage() {
  const { data: health, isLoading: healthLoading, isError: healthError } = useHealth()
  const { data: status, isLoading, isError } = useSystemStatus()

  const checklist = [
    { done: (status?.dataset_count ?? 0) > 0, label: 'Import a sensor dataset' },
    { done: (status?.model_count ?? 0) > 0, label: 'Train or register a recognition model' },
    { done: !!status?.latest_evaluation, label: 'Run an evaluation pass' },
    { done: status?.setup_complete ?? false, label: 'Open the Playground for recognition' },
  ]

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Monitor your local SLSL research workspace, system health, and next setup steps."
        action={
          <Button asChild variant="secondary">
            <Link to="/datasets"><Upload className="h-4 w-4" /> Import Dataset</Link>
          </Button>
        }
      />

      {(isLoading || healthLoading) && <LoadingCardGrid />}

      {(isError || healthError) && (
        <Alert variant="warning" className="mb-6">
          Backend is not reachable. Start the API server on port 8000, then refresh this page.
        </Alert>
      )}

      {status && (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Active model" value={status.active_model?.name ?? 'None'} hint={status.active_model?.version ?? 'No trained model yet'} icon={Brain} tone="accent" />
            <StatCard label="Datasets" value={String(status.dataset_count)} hint="Registered in SQLite" icon={Database} />
            <StatCard label="Models" value={String(status.model_count)} hint="Stored model records" icon={Brain} />
            <StatCard label="Backend" value={health?.status === 'ok' ? 'Healthy' : 'Unavailable'} hint={health?.service} icon={Activity} tone={health?.status === 'ok' ? 'success' : 'warning'} />
          </div>

          <div className="mt-6 grid gap-4 xl:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Research status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-border bg-surface-muted px-4 py-3">
                    <p className="text-xs text-muted">Latest training job</p>
                    <p className="mt-1 text-sm font-medium">{status.latest_training_job?.name ?? 'No training jobs yet'}</p>
                    <Badge variant="secondary" className="mt-2">{status.latest_training_job?.status ?? 'not_started'}</Badge>
                  </div>
                  <div className="rounded-lg border border-border bg-surface-muted px-4 py-3">
                    <p className="text-xs text-muted">Latest evaluation</p>
                    <p className="mt-1 text-sm font-medium">{status.latest_evaluation?.name ?? 'No evaluations yet'}</p>
                    <Badge variant="secondary" className="mt-2">{status.latest_evaluation?.status ?? 'not_started'}</Badge>
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Recent activity</p>
                  {status.recent_activity.length === 0 ? (
                    <p className="text-sm text-muted">No activity recorded yet. Actions will appear here as you import data and run jobs.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {status.recent_activity.map((item) => (
                        <li key={item.id} className="flex items-start justify-between gap-3 border-b border-border pb-2 last:border-0">
                          <span>{item.message}</span>
                          <span className="shrink-0 text-xs text-muted">{new Date(item.created_at).toLocaleString()}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Setup checklist</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {checklist.map((item) => (
                    <li key={item.label} className="flex items-center gap-3 text-sm">
                      {item.done ? (
                        <CheckCircle2 className="h-4 w-4 text-success" />
                      ) : (
                        <Circle className="h-4 w-4 text-border-strong" />
                      )}
                      <span className={item.done ? 'text-foreground' : 'text-muted'}>{item.label}</span>
                    </li>
                  ))}
                </ul>

                <div className="mt-6 space-y-2">
                  <Button asChild className="w-full" variant="secondary">
                    <Link to="/training"><Database className="h-4 w-4" /> Start Training</Link>
                  </Button>
                  <Button asChild className="w-full">
                    <Link to="/playground"><Play className="h-4 w-4" /> Open Playground <ArrowRight className="h-4 w-4" /></Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
