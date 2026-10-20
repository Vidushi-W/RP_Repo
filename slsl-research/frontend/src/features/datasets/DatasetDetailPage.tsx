import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useState } from 'react'
import { PageHeader } from '@/components/layout/PageHeader'
import { LoadingSpinner } from '@/components/shared/LoadingState'
import { Alert } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogBody, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { datasetApi } from '@/services/datasetApi'
import { maintenanceApi } from '@/services/maintenanceApi'
import { ImportWizard } from './ImportWizard'

export function DatasetDetailPage() {
  const { datasetId } = useParams()
  const id = Number(datasetId)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [showImport, setShowImport] = useState(false)
  const [importKey, setImportKey] = useState(0)

  const { data: dataset } = useQuery({ queryKey: ['dataset', id], queryFn: () => datasetApi.get(id), enabled: !!id })
  const { data: recordings = [] } = useQuery({ queryKey: ['recordings', id], queryFn: () => datasetApi.listRecordings(id), enabled: !!id })
  const { data: validation, refetch: refetchValidation } = useQuery({
    queryKey: ['dataset-validation', id],
    queryFn: () => datasetApi.validate(id),
    enabled: false,
  })

  const splitMutation = useMutation({
    mutationFn: () => datasetApi.assignSplits(id, { train_ratio: 0.7, val_ratio: 0.15, preserve_existing: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recordings', id] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () => maintenanceApi.deleteDataset(id, deleteConfirm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets'] })
      navigate('/datasets')
    },
  })

  if (!dataset) return <LoadingSpinner label="Loading dataset…" className="py-12" />

  const expectedDelete = dataset.provenance === 'real' ? `DELETE ${dataset.name}` : `DELETE ${dataset.id}`

  return (
    <div>
      <PageHeader
        title={dataset.name}
        description={dataset.description || 'Dataset detail, recordings, splits, and validation.'}
        breadcrumbs={[
          { label: 'Datasets', href: '/datasets' },
          { label: dataset.name },
        ]}
        action={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setImportKey((k) => k + 1); setShowImport(true) }}>Add Recordings</Button>
            <Button variant="secondary" onClick={() => refetchValidation()}>Run Validation</Button>
          </div>
        }
      />

      <div className="mb-5 flex flex-wrap gap-2 text-sm">
        <Badge variant="secondary">v{dataset.current_version}</Badge>
        <Badge variant="secondary">{dataset.provenance}</Badge>
        <Badge variant={dataset.status === 'ready' ? 'success' : 'secondary'}>{dataset.status}</Badge>
        <span className="text-muted">{dataset.recording_count} recordings</span>
      </div>

      <Tabs defaultValue="recordings">
        <TabsList>
          <TabsTrigger value="recordings">Recordings</TabsTrigger>
          <TabsTrigger value="splits">Splits</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
        </TabsList>

        <TabsContent value="recordings">
          <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
            <table className="data-table min-w-full">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Gloss sequence</th>
                  <th>Emotion</th>
                  <th>Split</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {recordings.map((r) => (
                  <tr key={r.recording_id}>
                    <td>
                      <Link className="font-medium text-accent hover:underline" to={`/datasets/${id}/recordings/${r.recording_id}`}>
                        {r.recording_id}
                      </Link>
                    </td>
                    <td>{r.ordered_sign_labels || '—'}</td>
                    <td className="capitalize">{r.emotion_label}</td>
                    <td>{r.split}</td>
                    <td>{(r.duration_ms / 1000).toFixed(2)} s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="splits">
          <Card>
            <CardContent className="space-y-3 pt-4 text-sm">
              <p className="text-muted">Assign train / validation / test splits by recording group. Default ratio 70/15/15.</p>
              <Alert variant="warning">Synthetic signer IDs (e.g. SYNTHETIC_SIGNER_01) are artificial identifiers, not human participants.</Alert>
              <Button variant="secondary" onClick={() => splitMutation.mutate()} disabled={splitMutation.isPending}>
                Apply 70/15/15 Split
              </Button>
              {splitMutation.data && (
                <pre className="rounded-lg bg-surface-muted p-3 text-xs">{JSON.stringify(splitMutation.data, null, 2)}</pre>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="validation">
          {validation ? (
            <Card>
              <CardContent className="space-y-2 pt-4 text-sm">
                <p>Valid: {validation.valid_recordings} · Invalid: {validation.invalid_recordings}</p>
                <p>Split counts: {JSON.stringify(validation.split_counts)}</p>
                {validation.split_isolation_errors.map((e) => <p key={e} className="text-danger">{e}</p>)}
                {validation.issues.map((e) => <p key={e} className="text-warning">{e}</p>)}
              </CardContent>
            </Card>
          ) : (
            <p className="text-sm text-muted">Run validation to see the dataset report.</p>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={showImport} onOpenChange={setShowImport}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Add recordings</DialogTitle>
            <DialogDescription>Import more sensor CSV or ZIP files into {dataset.name}.</DialogDescription>
          </DialogHeader>
          <DialogBody className="pt-0">
            <ImportWizard key={importKey} embedded datasetId={id} datasetName={dataset.name} onClose={() => setShowImport(false)} />
          </DialogBody>
        </DialogContent>
      </Dialog>

      <Card className="mt-8 border-danger/20 bg-danger-soft/30">
        <CardHeader>
          <CardTitle className="text-danger">Delete dataset</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted">Removes all recordings and files. Type <code className="rounded bg-surface px-1 font-mono text-xs">{expectedDelete}</code> to confirm.</p>
          <div className="space-y-1.5">
            <Label htmlFor="delete-confirm">Confirmation</Label>
            <Input id="delete-confirm" placeholder={expectedDelete} value={deleteConfirm} onChange={(e) => setDeleteConfirm(e.target.value)} />
          </div>
          <Button variant="destructive" size="sm" disabled={deleteConfirm !== expectedDelete || deleteMutation.isPending} onClick={() => deleteMutation.mutate()}>
            Delete dataset permanently
          </Button>
          {deleteMutation.error && <Alert variant="danger">{(deleteMutation.error as Error).message}</Alert>}
        </CardContent>
      </Card>
    </div>
  )
}
