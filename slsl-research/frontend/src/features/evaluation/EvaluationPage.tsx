import { BarChart3 } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useSystemStatus } from '@/hooks/useSystemStatus'

export function EvaluationPage() {
  const { data: status } = useSystemStatus()

  return (
    <div>
      <PageHeader
        title="Evaluation"
        description="Review sequence accuracy, error patterns, and synthetic-vs-real result separation."
        action={<Button disabled>Run Evaluation</Button>}
      />

      <Tabs defaultValue="runs">
        <TabsList>
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="synthetic">Synthetic</TabsTrigger>
          <TabsTrigger value="real">Real user</TabsTrigger>
        </TabsList>

        <TabsContent value="runs">
          {!status?.latest_evaluation ? (
            <EmptyState
              icon={BarChart3}
              title="No evaluation runs yet"
              description="Evaluation will be added in a later step. Metrics will never be fabricated before a real run completes."
            />
          ) : (
            <p className="text-sm">{status.latest_evaluation.name}</p>
          )}
        </TabsContent>
        <TabsContent value="synthetic">
          <EmptyState
            icon={BarChart3}
            title="Synthetic prototype results"
            description="Prototype metrics from synthetic sensor data will be stored separately and clearly labelled when available."
          />
        </TabsContent>
        <TabsContent value="real">
          <EmptyState
            icon={BarChart3}
            title="Real user results not collected"
            description="This section stays empty until consented recordings from SLSL users are imported and evaluated."
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
