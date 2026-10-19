import { Brain, SlidersHorizontal } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function TrainingPage() {
  return (
    <div>
      <PageHeader
        title="Training"
        description="Configure and launch CPU-friendly model training jobs for continuous sign recognition."
        action={<Button disabled>Start Training</Button>}
      />

      <Tabs defaultValue="jobs">
        <TabsList>
          <TabsTrigger value="jobs">Jobs</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="jobs">
          <EmptyState
            icon={Brain}
            title="No training jobs yet"
            description="Model training is planned for Step 2. Jobs will track status, checkpoints, and linked datasets without blocking the dashboard."
          />
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4" /> Beginner settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-[var(--color-muted)]">
              <p>Training controls will appear here once the pipeline is implemented.</p>
              <details className="rounded-lg border border-[var(--color-border)] bg-slate-50 px-4 py-3">
                <summary className="cursor-pointer font-medium text-[var(--color-foreground)]">Advanced parameters</summary>
                <p className="mt-2">Batch size, learning rate, CTC settings, and epoch limits will be exposed in a later milestone.</p>
              </details>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
