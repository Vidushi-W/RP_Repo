import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Play, RotateCcw, Square } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { datasetApi } from '@/services/datasetApi'
import { trainingApi } from '@/services/trainingApi'
import type { TrainingPreview } from '@/types/training'

export function TrainingPage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState('new')
  const [datasetId, setDatasetId] = useState<number | null>(null)
  const [preview, setPreview] = useState<TrainingPreview | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [epochs, setEpochs] = useState(20)
  const [batchSize, setBatchSize] = useState(4)
  const [lr, setLr] = useState(0.001)
  const [trainingMode, setTrainingMode] = useState('fresh')
  const [resetConfirm, setResetConfirm] = useState('')

  const { data: datasets = [] } = useQuery({ queryKey: ['datasets'], queryFn: datasetApi.list })
  const { data: jobs = [], refetch: refetchJobs } = useQuery({
    queryKey: ['training-jobs'],
    queryFn: trainingApi.listJobs,
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === 'running' || j.status === 'queued') ? 3000 : false),
  })
  const { data: models = [], refetch: refetchModels } = useQuery({ queryKey: ['models'], queryFn: () => trainingApi.listModels(true) })

  const previewMutation = useMutation({
    mutationFn: () => trainingApi.preview(datasetId!),
    onSuccess: setPreview,
  })

  const startMutation = useMutation({
    mutationFn: () =>
      trainingApi.start({
        dataset_id: datasetId!,
        training_mode: trainingMode,
        epochs,
        batch_size: batchSize,
        learning_rate: lr,
        model_name: `CTC Model — ${datasets.find((d) => d.id === datasetId)?.name}`,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['training-jobs'] })
      setTab('runs')
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (id: number) => trainingApi.cancelJob(id),
    onSuccess: () => refetchJobs(),
  })

  const activateMutation = useMutation({
    mutationFn: (id: number) => trainingApi.activateModel(id),
    onSuccess: () => { refetchModels(); qc.invalidateQueries({ queryKey: ['system-status'] }) },
  })

  const archiveMutation = useMutation({
    mutationFn: (id: number) => trainingApi.archiveModel(id),
    onSuccess: () => refetchModels(),
  })

  const resetMutation = useMutation({
    mutationFn: () =>
      trainingApi.resetExecute({
        archive_models: true,
        clear_jobs: false,
        delete_checkpoints: false,
        confirmation: resetConfirm,
      }),
    onSuccess: () => { refetchModels(); refetchJobs(); qc.invalidateQueries({ queryKey: ['system-status'] }) },
  })

  const statusTone = (s: string) => {
    if (s === 'completed') return 'success'
    if (s === 'running') return 'default'
    if (s === 'failed' || s === 'cancelled') return 'warning'
    return 'secondary'
  }

  return (
    <div>
      <PageHeader
        title="Training"
        description="Train continuous sign recognition models on versioned datasets. Jobs run in a separate local process."
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="new">New Training</TabsTrigger>
          <TabsTrigger value="runs">Training Runs</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
        </TabsList>

        <TabsContent value="new">
          <Card>
            <CardHeader><CardTitle>Choose Dataset → Configure → Review → Start</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[var(--color-muted)]">Dataset</label>
                <select className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={datasetId ?? ''} onChange={(e) => { setDatasetId(Number(e.target.value)); setPreview(null) }}>
                  <option value="">Select dataset…</option>
                  {datasets.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.recording_count} recordings)</option>)}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-[var(--color-muted)]">Training mode</label>
                <select className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={trainingMode} onChange={(e) => setTrainingMode(e.target.value)}>
                  <option value="fresh">Start Fresh Training (recommended)</option>
                  <option value="finetune">Fine-tune from checkpoint (domain shift warning)</option>
                </select>
              </div>

              <div className="grid gap-4 md:grid-cols-3">
                <div><label className="text-xs text-[var(--color-muted)]">Epochs</label><input type="number" className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={epochs} onChange={(e) => setEpochs(Number(e.target.value))} /></div>
                <div><label className="text-xs text-[var(--color-muted)]">Batch size</label><input type="number" className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={batchSize} onChange={(e) => setBatchSize(Number(e.target.value))} /></div>
                <div><label className="text-xs text-[var(--color-muted)]">Learning rate</label><input type="number" step="0.0001" className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={lr} onChange={(e) => setLr(Number(e.target.value))} /></div>
              </div>

              <button type="button" className="text-sm text-indigo-700" onClick={() => setShowAdvanced(!showAdvanced)}>
                {showAdvanced ? 'Hide' : 'Show'} advanced options
              </button>
              {showAdvanced && <p className="text-xs text-[var(--color-muted)]">CNN channels: 32 · BiLSTM hidden: 32 · CTC blank index: 0 · CPU-only PyTorch</p>}

              <div className="flex gap-2">
                <Button variant="secondary" disabled={!datasetId} onClick={() => previewMutation.mutate()}>Review Settings</Button>
                <Button disabled={!datasetId || !preview || startMutation.isPending} onClick={() => startMutation.mutate()}>
                  <Play className="h-4 w-4" /> Start Training
                </Button>
              </div>

              {preview && (
                <div className="rounded-lg border bg-slate-50 p-4 text-sm space-y-1">
                  <p><strong>Train:</strong> {preview.train_count} · <strong>Val:</strong> {preview.val_count} · <strong>Test (held out):</strong> {preview.test_count}</p>
                  <p><strong>Vocabulary:</strong> {preview.vocabulary_size} · <strong>Provenance:</strong> {preview.provenance}</p>
                  <p><strong>Schema:</strong> {preview.schema_compatible ? 'Compatible' : 'Issues detected'}</p>
                  {preview.warnings.map((w) => <p key={w} className="text-amber-800">{w}</p>)}
                </div>
              )}
              {(startMutation.error || previewMutation.error) && (
                <p className="text-sm text-rose-700">{((startMutation.error || previewMutation.error) as Error).message}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="runs">
          {jobs.length === 0 ? (
            <p className="text-sm text-[var(--color-muted)]">No training runs yet.</p>
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="rounded-xl border bg-white p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="font-medium">{job.name}</p>
                      <p className="text-xs text-[var(--color-muted)]">{job.message}</p>
                    </div>
                    <Badge variant={statusTone(job.status)}>{job.status}</Badge>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-4 text-xs text-[var(--color-muted)]">
                    <span>Epoch {job.current_epoch}/{job.total_epochs}</span>
                    <span>Train loss: {job.train_loss?.toFixed(4) ?? '—'}</span>
                    <span>Val loss: {job.val_loss?.toFixed(4) ?? '—'}</span>
                    <span>Val WER: {job.val_wer?.toFixed(3) ?? '—'}</span>
                  </div>
                  {(job.status === 'running' || job.status === 'queued') && (
                    <Button size="sm" variant="secondary" className="mt-3" onClick={() => cancelMutation.mutate(job.id)}>
                      <Square className="h-3 w-3" /> Cancel
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="models">
          {models.length === 0 ? (
            <p className="text-sm text-[var(--color-muted)]">No models in registry yet. Complete a training run first.</p>
          ) : (
            <div className="space-y-3">
              {models.map((m) => (
                <div key={m.id} className="rounded-xl border bg-white p-4 text-sm">
                  <div className="flex flex-wrap justify-between gap-2">
                    <div>
                      <p className="font-medium">{m.name} <span className="text-[var(--color-muted)]">v{m.version}</span></p>
                      <p className="text-xs text-[var(--color-muted)]">{m.architecture} · {m.provenance} · {m.vocabulary.length} signs</p>
                    </div>
                    <Badge variant={m.status === 'active' ? 'success' : 'secondary'}>{m.status}{m.is_archived ? ' (archived)' : ''}</Badge>
                  </div>
                  <p className="mt-2 text-xs">WER: {(m.validation_metrics.final_val_wer as number)?.toFixed(3) ?? '—'} · Emotion: {m.emotion_available ? 'available' : 'unavailable'}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {!m.is_archived && m.status !== 'active' && (
                      <Button size="sm" onClick={() => activateMutation.mutate(m.id)}>Activate</Button>
                    )}
                    {!m.is_archived && (
                      <Button size="sm" variant="secondary" onClick={() => archiveMutation.mutate(m.id)}>Archive</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          <Card className="mt-6">
            <CardHeader><CardTitle className="flex items-center gap-2"><RotateCcw className="h-4 w-4" /> Reset Training Workspace</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-[var(--color-muted)]">Deactivate models and archive checkpoints. Defaults to archiving, not deleting. Real recordings and annotations are preserved.</p>
              <input className="w-full rounded-md border px-3 py-2" placeholder="Type RESET to confirm" value={resetConfirm} onChange={(e) => setResetConfirm(e.target.value)} />
              <Button variant="secondary" disabled={resetConfirm !== 'RESET'} onClick={() => resetMutation.mutate()}>Reset Workspace</Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
