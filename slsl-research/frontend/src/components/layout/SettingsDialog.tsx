import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Settings } from 'lucide-react'
import { useState } from 'react'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { maintenanceApi } from '@/services/maintenanceApi'
import { settingsApi } from '@/services/settingsApi'

export function SettingsDialog() {
  const [open, setOpen] = useState(false)
  const [resetConfirm, setResetConfirm] = useState('')
  const [deleteDatasetConfirm, setDeleteDatasetConfirm] = useState('')
  const [deleteDatasetId, setDeleteDatasetId] = useState('')
  const qc = useQueryClient()

  const { data: settings } = useQuery({
    queryKey: ['studio-settings'],
    queryFn: settingsApi.get,
    enabled: open,
  })
  const { data: storage, refetch: refetchStorage } = useQuery({
    queryKey: ['storage-summary'],
    queryFn: maintenanceApi.storage,
    enabled: open,
  })

  const saveMutation = useMutation({
    mutationFn: (patch: { torch_threads?: number; uncertainty_threshold?: number }) => settingsApi.update(patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['studio-settings'] }),
  })

  const exportMutation = useMutation({
    mutationFn: settingsApi.exportMetadata,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `slsl-studio-export-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const resetMutation = useMutation({
    mutationFn: (scope: 'training' | 'synthetic' | 'all') =>
      maintenanceApi.resetDatabase(scope, resetConfirm, scope === 'all'),
    onSuccess: () => {
      qc.invalidateQueries()
      refetchStorage()
      setResetConfirm('')
    },
  })

  const deleteDatasetMutation = useMutation({
    mutationFn: () => maintenanceApi.deleteDataset(Number(deleteDatasetId), deleteDatasetConfirm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets'] })
      refetchStorage()
      setDeleteDatasetId('')
      setDeleteDatasetConfirm('')
    },
  })

  const clearHistoryMutation = useMutation({
    mutationFn: maintenanceApi.clearRecognitionHistory,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['playground-history'] }),
  })

  const clearEvalsMutation = useMutation({
    mutationFn: maintenanceApi.clearEvaluations,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['evaluation-runs'] }),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-surface-muted hover:text-foreground"
        >
          <Settings className="h-4 w-4" /> Settings
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Studio Settings</DialogTitle>
          <DialogDescription>Configure paths, performance, and data management.</DialogDescription>
        </DialogHeader>
        <DialogBody className="pt-0">
          <Tabs defaultValue="general">
            <TabsList className="w-full">
              <TabsTrigger value="general" className="flex-1">General</TabsTrigger>
              <TabsTrigger value="data" className="flex-1">Data Management</TabsTrigger>
            </TabsList>

            <TabsContent value="general">
              {settings && (
                <div className="space-y-4 text-sm">
                  <div>
                    <Label>Data directory</Label>
                    <p className="mt-1 font-mono text-xs break-all text-muted">{settings.data_dir}</p>
                  </div>
                  <div>
                    <Label>Artifacts directory</Label>
                    <p className="mt-1 font-mono text-xs break-all text-muted">{settings.artifacts_dir}</p>
                  </div>
                  <div>
                    <Label>Database</Label>
                    <p className="mt-1 font-mono text-xs break-all text-muted">{settings.database_url}</p>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="torch-threads">CPU threads for training</Label>
                    <Input id="torch-threads" type="number" min={1} max={8} value={settings.torch_threads} onChange={(e) => saveMutation.mutate({ torch_threads: Number(e.target.value) })} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="uncertainty">Uncertainty threshold</Label>
                    <Input id="uncertainty" type="number" step={0.05} min={0} max={1} value={settings.uncertainty_threshold} onChange={(e) => saveMutation.mutate({ uncertainty_threshold: Number(e.target.value) })} />
                  </div>
                  <Button variant="secondary" onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>Export metadata backup</Button>
                </div>
              )}
            </TabsContent>

            <TabsContent value="data">
              {storage && (
                <div className="space-y-5 text-sm">
                  <div className="rounded-lg border border-border bg-surface-muted p-3 text-xs space-y-1">
                    <p>Database: {maintenanceApi.formatBytes(storage.database_size_bytes)}</p>
                    <p>Data files: {maintenanceApi.formatBytes(storage.data_dir_size_bytes)}</p>
                    <p>Artifacts: {maintenanceApi.formatBytes(storage.artifacts_dir_size_bytes)}</p>
                    <p className="pt-1">Datasets {storage.counts.datasets} · Recordings {storage.counts.recordings} · Models {storage.counts.models}</p>
                  </div>

                  <div className="space-y-2">
                    <p className="font-medium">Delete a dataset</p>
                    <Input placeholder="Dataset ID" value={deleteDatasetId} onChange={(e) => setDeleteDatasetId(e.target.value)} />
                    <Input placeholder="Type DELETE {id} or DELETE {name}" value={deleteDatasetConfirm} onChange={(e) => setDeleteDatasetConfirm(e.target.value)} />
                    <Button variant="secondary" size="sm" disabled={!deleteDatasetId || !deleteDatasetConfirm} onClick={() => deleteDatasetMutation.mutate()}>Delete dataset</Button>
                    {deleteDatasetMutation.error && <Alert variant="danger">{(deleteDatasetMutation.error as Error).message}</Alert>}
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button variant="secondary" size="sm" onClick={() => clearHistoryMutation.mutate()}>Clear recognition history</Button>
                    <Button variant="secondary" size="sm" onClick={() => clearEvalsMutation.mutate()}>Clear evaluations</Button>
                  </div>

                  <Alert variant="warning">
                    <p className="flex items-center gap-1 font-medium"><AlertTriangle className="h-3.5 w-3.5" /> Database reset</p>
                    <p className="mt-2 text-xs">Type RESET TRAINING, RESET SYNTHETIC, or RESET DATABASE to confirm.</p>
                    <Input className="mt-2" placeholder="RESET TRAINING / RESET SYNTHETIC / RESET DATABASE" value={resetConfirm} onChange={(e) => setResetConfirm(e.target.value)} />
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button variant="secondary" size="sm" disabled={resetConfirm !== 'RESET TRAINING'} onClick={() => resetMutation.mutate('training')}>Reset training</Button>
                      <Button variant="secondary" size="sm" disabled={resetConfirm !== 'RESET SYNTHETIC'} onClick={() => resetMutation.mutate('synthetic')}>Remove synthetic</Button>
                      <Button variant="secondary" size="sm" disabled={resetConfirm !== 'RESET DATABASE'} onClick={() => resetMutation.mutate('all')}>Reset database</Button>
                    </div>
                    {resetMutation.error && <p className="mt-2 text-xs text-danger">{(resetMutation.error as Error).message}</p>}
                  </Alert>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
