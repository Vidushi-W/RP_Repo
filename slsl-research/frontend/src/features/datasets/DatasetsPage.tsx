import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen, Sparkles, Upload } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { LoadingSpinner } from '@/components/shared/LoadingState'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { datasetApi } from '@/services/datasetApi'
import { DatasetList } from './DatasetList'
import { ImportWizard } from './ImportWizard'

export function DatasetsPage() {
  const [showImport, setShowImport] = useState(false)
  const [importKey, setImportKey] = useState(0)
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

  const openImport = () => {
    setImportKey((k) => k + 1)
    setShowImport(true)
  }

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
            <Button onClick={openImport}>
              <Upload className="h-4 w-4" /> Import Dataset
            </Button>
          </div>
        }
      />

      {synthMutation.isError && (
        <Alert variant="danger" className="mb-4">{(synthMutation.error as Error).message}</Alert>
      )}

      <Tabs defaultValue="library">
        <TabsList>
          <TabsTrigger value="library">Library</TabsTrigger>
          <TabsTrigger value="imports">Import history</TabsTrigger>
        </TabsList>

        <TabsContent value="library">
          {isLoading ? (
            <LoadingSpinner label="Loading datasets…" />
          ) : datasets.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="No datasets yet"
              description="Generate a synthetic prototype dataset or import sensor CSV files with a separate manifest for labels and splits."
              action={
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => synthMutation.mutate()} disabled={synthMutation.isPending}>Generate Synthetic</Button>
                  <Button onClick={openImport}>Import Dataset</Button>
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
                <div key={job.id} className="flex items-center justify-between rounded-xl border border-border bg-surface px-4 py-3 text-sm shadow-sm">
                  <div>
                    <p className="font-medium">{job.source_name}</p>
                    <p className="text-xs text-muted">{new Date(job.created_at).toLocaleString()}</p>
                  </div>
                  <Badge variant={job.status === 'completed' ? 'success' : 'secondary'}>{job.status}</Badge>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={showImport} onOpenChange={setShowImport}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Import dataset</DialogTitle>
            <DialogDescription>Upload sensor CSV files or a ZIP package with optional manifest metadata.</DialogDescription>
          </DialogHeader>
          <DialogBody className="pt-0">
            <ImportWizard key={importKey} embedded onClose={() => setShowImport(false)} />
          </DialogBody>
        </DialogContent>
      </Dialog>
    </div>
  )
}
