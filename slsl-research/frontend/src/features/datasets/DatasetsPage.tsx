import { FolderOpen, Upload } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useSystemStatus } from '@/hooks/useSystemStatus'

export function DatasetsPage() {
  const { data: status } = useSystemStatus()

  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Manage sensor recordings, provenance metadata, and import pipelines for two-glove CSV data."
        action={
          <Button disabled>
            <Upload className="h-4 w-4" /> Import Dataset
          </Button>
        }
      />

      <Tabs defaultValue="library">
        <TabsList>
          <TabsTrigger value="library">Library</TabsTrigger>
          <TabsTrigger value="imports">Imports</TabsTrigger>
        </TabsList>
        <TabsContent value="library">
          {status?.dataset_count === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="No datasets registered yet"
              description="Dataset import will be added in Step 2. Recordings will appear here with provenance, signer metadata, and split assignments."
              action={<Button disabled variant="secondary">Import coming in Step 2</Button>}
            />
          ) : (
            <p className="text-sm text-[var(--color-muted)]">{status?.dataset_count} dataset records found.</p>
          )}
        </TabsContent>
        <TabsContent value="imports">
          <EmptyState
            icon={Upload}
            title="No import jobs"
            description="CSV import history and validation results will be tracked here once the import pipeline is implemented."
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
