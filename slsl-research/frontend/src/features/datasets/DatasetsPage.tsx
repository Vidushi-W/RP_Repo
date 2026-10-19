import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen, Sparkles, Upload } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { datasetApi } from '@/services/datasetApi'
import { DatasetList } from './DatasetList'
import { ImportWizard } from './ImportWizard'

export function DatasetsPage() {
  const [showImport, setShowImport] = useState(false)
  const qc = useQueryClient()
  const { data: datasets = [], isLoading } = useQuery({ queryKey: ['datasets'], queryFn: datasetApi.list })
  const { data: imports = [] } = useQuery({ queryKey: ['imports'], queryFn: datasetApi.listImports })

  const synthMutation = useMutation({
    mutationFn: () =>
      datasetApi.generateSynthetic({
        name: 'Synthetic Prototype Dataset',
        description: 'Artificial two-glove sensor patterns for pipeline development. Not genuine SLSL recordings.',
        total_recordings: 400,
        seed: 42,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets'] })
      qc.invalidateQueries({ queryKey: ['system-status'] })
    },
  })

  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Import, annotate, and version two-glove sensor recordings with metadata kept separate from sensor CSVs."
        action={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => synthMutation.mutate()} disabled={synthMutation.isPending}>
              <Sparkles className="h-4 w-4" /> Generate Synthetic
            </Button>
            <Button onClick={() => setShowImport(true)}>
              <Upload className="h-4 w-4" /> Import Dataset
            </Button>
          </div>
        }
      />

      {synthMutation.isError && (
        <p className="mb-4 text-sm text-rose-700">{(synthMutation.error as Error).message}</p>
      )}

      <Tabs defaultValue="library">
        <TabsList>
          <TabsTrigger value="library">Library</TabsTrigger>
          <TabsTrigger value="imports">Imports</TabsTrigger>
        </TabsList>

        <TabsContent value="library">
          {isLoading ? (
            <p className="text-sm text-[var(--color-muted)]">Loading datasets…</p>
          ) : datasets.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="No datasets yet"
              description="Generate a synthetic prototype dataset or import sensor CSV files with a separate manifest for labels and splits."
              action={
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => synthMutation.mutate()} disabled={synthMutation.isPending}>Generate Synthetic</Button>
                  <Button onClick={() => setShowImport(true)}>Import Dataset</Button>
                </div>
              }
            />
          ) : (
            <DatasetList datasets={datasets} />
          )}
        </TabsContent>

        <TabsContent value="imports">
          {imports.length === 0 ? (
            <EmptyState icon={Upload} title="No import jobs yet" description="Import history will appear here after your first dataset import." />
          ) : (
            <div className="space-y-2">
              {imports.map((job) => (
                <div key={job.id} className="rounded-lg border border-[var(--color-border)] bg-white px-4 py-3 text-sm">
                  <div className="flex justify-between"><span className="font-medium">{job.source_name}</span><span>{job.status}</span></div>
                  <p className="text-xs text-[var(--color-muted)]">{new Date(job.created_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {showImport && (
        <div className="mt-6">
          <ImportWizard onClose={() => setShowImport(false)} />
        </div>
      )}
    </div>
  )
}
