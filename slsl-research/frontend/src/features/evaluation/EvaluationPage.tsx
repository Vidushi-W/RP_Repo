import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { AlertTriangle, BarChart3, CheckCircle2, ChevronRight, FlaskConical, Play, Users } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { SensorChart } from '@/components/shared/SensorChart'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { datasetApi } from '@/services/datasetApi'
import { evaluationApi } from '@/services/evaluationApi'
import { trainingApi } from '@/services/trainingApi'
import type { AlignmentStep, PredictionRow } from '@/types/evaluation'

const STEPS = ['Choose Model', 'Choose Dataset', 'Compatibility', 'Run', 'Results']

function stepClass(active: boolean, done: boolean) {
  if (active) return 'border-indigo-600 bg-indigo-50 text-indigo-800'
  if (done) return 'border-emerald-300 bg-emerald-50 text-emerald-800'
  return 'border-slate-200 bg-white text-slate-500'
}

function AlignmentView({ alignment }: { alignment: AlignmentStep[] }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {alignment.map((s, i) => {
        const tone =
          s.op === 'match' ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
          : s.op === 'substitution' ? 'bg-amber-50 text-amber-900 border-amber-200'
          : s.op === 'insertion' ? 'bg-sky-50 text-sky-900 border-sky-200'
          : 'bg-rose-50 text-rose-900 border-rose-200'
        const label = s.op === 'match' ? `${s.ref}` : s.op === 'substitution' ? `${s.ref}→${s.pred}` : s.op === 'insertion' ? `+${s.pred}` : `−${s.ref}`
        return <span key={i} className={`rounded border px-2 py-0.5 text-xs font-medium ${tone}`} title={s.op}>{label}</span>
      })}
    </div>
  )
}

function PredictionDetail({ row, datasetId }: { row: PredictionRow; datasetId: number }) {
  const { data } = useQuery({
    queryKey: ['recording', datasetId, row.recording_id],
    queryFn: () => datasetApi.getRecording(datasetId, row.recording_id),
    enabled: !!datasetId && !!row.recording_id,
  })

  return (
    <div className="space-y-4 text-sm">
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-xs font-medium text-[var(--color-muted)]">Reference signs</p>
          <p className="mt-1 font-mono">{row.reference_signs.join(' | ') || '—'}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-[var(--color-muted)]">Predicted signs</p>
          <p className="mt-1 font-mono">{row.predicted_signs.join(' | ') || '—'}</p>
        </div>
      </div>
      <div>
        <p className="text-xs font-medium text-[var(--color-muted)]">Token alignment</p>
        <div className="mt-2"><AlignmentView alignment={row.alignment} /></div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <p className="text-xs text-[var(--color-muted)]">Reference English</p>
          <p>{row.reference_english ?? '—'}</p>
        </div>
        <div>
          <p className="text-xs text-[var(--color-muted)]">Generated English (from predicted glosses)</p>
          <p>{row.generated_english || '—'}</p>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3 text-xs">
        <div><span className="text-[var(--color-muted)]">Emotion ref:</span> {row.reference_emotion ?? 'n/a'}</div>
        <div><span className="text-[var(--color-muted)]">Emotion pred:</span> {row.predicted_emotion ?? 'unavailable'}</div>
        <div><span className="text-[var(--color-muted)]">Latency:</span> {row.inference_ms.toFixed(1)} ms</div>
      </div>
      <p className="text-xs text-[var(--color-muted)]">
        Decoder score ({row.decoder_score_label}): {row.decoder_score.toFixed(3)} — not a calibrated correctness probability.
      </p>
      {data && (
        <div className="grid gap-3 lg:grid-cols-2">
          <SensorChart title="Left-hand movement" series={data.visualization.left_motion} color="#4f46e5" />
          <SensorChart title="Right-hand movement" series={data.visualization.right_motion} color="#0891b2" />
        </div>
      )}
    </div>
  )
}

export function EvaluationPage() {
  const qc = useQueryClient()
  const [step, setStep] = useState(0)
  const [modelId, setModelId] = useState<number | null>(null)
  const [datasetId, setDatasetId] = useState<number | null>(null)
  const [split, setSplit] = useState('test')
  const [activeRunId, setActiveRunId] = useState<number | null>(null)
  const [selectedPred, setSelectedPred] = useState<PredictionRow | null>(null)
  const [filter, setFilter] = useState('all')
  const [compareIds, setCompareIds] = useState<number[]>([])

  const { data: models = [] } = useQuery({ queryKey: ['models'], queryFn: () => trainingApi.listModels(false) })
  const { data: datasets = [] } = useQuery({ queryKey: ['datasets'], queryFn: datasetApi.list })
  const { data: runs = [], refetch: refetchRuns } = useQuery({ queryKey: ['evaluation-runs'], queryFn: () => evaluationApi.listRuns() })

  const { data: preview, refetch: refetchPreview } = useQuery({
    queryKey: ['eval-preview', modelId, datasetId, split],
    queryFn: () => evaluationApi.preview(modelId!, datasetId!, split),
    enabled: !!modelId && !!datasetId,
  })

  const { data: results } = useQuery({
    queryKey: ['eval-results', activeRunId],
    queryFn: () => evaluationApi.getResults(activeRunId!),
    enabled: !!activeRunId,
  })

  const runMutation = useMutation({
    mutationFn: () => evaluationApi.run({
      model_id: modelId!,
      dataset_id: datasetId!,
      split,
      name: `Eval — ${models.find((m) => m.id === modelId)?.name}`,
    }),
    onSuccess: (run) => {
      setActiveRunId(run.id)
      setStep(4)
      refetchRuns()
      qc.invalidateQueries({ queryKey: ['system-status'] })
    },
  })

  const filteredPredictions = useMemo(() => {
    if (!results) return []
    return results.predictions.filter((p) => {
      if (filter === 'correct') return p.exact_match
      if (filter === 'incorrect') return !p.exact_match
      if (filter === 'uncertain') return p.high_uncertainty
      if (filter === 'emotion') return p.emotion_mismatch
      return true
    })
  }, [results, filter])

  const selectedModel = models.find((m) => m.id === modelId)
  const provenanceBadge = results?.run.provenance === 'real' ? 'Real SLSL' : 'Synthetic prototype'

  return (
    <div>
      <PageHeader
        title="Evaluation"
        description="Measure genuine sign-sequence predictions on held-out sensor recordings. Reference labels are compared only after inference."
      />

      <div className="mb-6 flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${stepClass(step === i, step > i)}`}>
            <span>{i + 1}</span> {label}
            {i < STEPS.length - 1 && <ChevronRight className="h-3 w-3 opacity-40" />}
          </div>
        ))}
      </div>

      <Tabs defaultValue="workflow">
        <TabsList>
          <TabsTrigger value="workflow">Workflow</TabsTrigger>
          <TabsTrigger value="history">Experiment History</TabsTrigger>
        </TabsList>

        <TabsContent value="workflow" className="space-y-4">
          {step === 0 && (
            <Card>
              <CardHeader><CardTitle>1. Choose Model</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <select className="w-full rounded-md border px-3 py-2 text-sm" value={modelId ?? ''} onChange={(e) => setModelId(Number(e.target.value))}>
                  <option value="">Select trained model…</option>
                  {models.filter((m) => !m.is_archived).map((m) => (
                    <option key={m.id} value={m.id}>{m.name} v{m.version} · {m.provenance}</option>
                  ))}
                </select>
                {selectedModel && (
                  <div className="rounded-lg bg-slate-50 p-3 text-xs space-y-1">
                    <p><strong>Architecture:</strong> {selectedModel.architecture}</p>
                    <p><strong>Provenance:</strong> {selectedModel.provenance}</p>
                    <p><strong>Vocabulary:</strong> {selectedModel.vocabulary.length} signs</p>
                    <p><strong>Emotion:</strong> {selectedModel.emotion_available ? 'available' : 'unavailable'}</p>
                  </div>
                )}
                <Button disabled={!modelId} onClick={() => setStep(1)}>Continue</Button>
              </CardContent>
            </Card>
          )}

          {step === 1 && (
            <Card>
              <CardHeader><CardTitle>2. Choose Dataset</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <select className="w-full rounded-md border px-3 py-2 text-sm" value={datasetId ?? ''} onChange={(e) => setDatasetId(Number(e.target.value))}>
                  <option value="">Select evaluation dataset…</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>{d.name} · {d.provenance} · {d.recording_count} rec</option>
                  ))}
                </select>
                <div>
                  <label className="text-xs text-[var(--color-muted)]">Evaluation split</label>
                  <select className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={split} onChange={(e) => setSplit(e.target.value)}>
                    <option value="test">Test (held out — recommended)</option>
                    <option value="val">Validation (diagnostic only)</option>
                    <option value="train">Train (not for final reporting)</option>
                  </select>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setStep(0)}>Back</Button>
                  <Button disabled={!datasetId} onClick={() => { refetchPreview(); setStep(2) }}>Check Compatibility</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {step === 2 && preview && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  3. Compatibility
                  <Badge variant={preview.compatible ? 'success' : 'warning'}>{preview.compatible ? 'Ready' : 'Review warnings'}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-[var(--color-muted)]">Splits</p>
                    <p className="mt-1">Train {preview.split_counts.train ?? 0} · Val {preview.split_counts.val ?? 0} · Test {preview.split_counts.test ?? 0}</p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-[var(--color-muted)]">Selected split</p>
                    <p className="mt-1 font-medium">{preview.split} ({preview.split_counts[preview.split] ?? 0} recordings)</p>
                    <p className="text-xs text-indigo-700">Recommended: {preview.recommended_split}</p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-xs text-[var(--color-muted)] flex items-center gap-1"><Users className="h-3 w-3" /> Signers</p>
                    <p className="mt-1 text-xs">{preview.signer_analysis.note}</p>
                  </div>
                </div>
                {preview.vocabulary_warnings.map((w) => <p key={w} className="text-amber-800">{w}</p>)}
                {preview.warnings.map((w) => <p key={w} className="text-amber-800 flex items-start gap-1"><AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />{w}</p>)}
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
                  <Button onClick={() => setStep(3)}>Continue to Run</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {step === 3 && (
            <Card>
              <CardHeader><CardTitle>4. Run Evaluation</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-[var(--color-muted)]">
                  Inference uses sensor CSV features only. Gloss labels are compared after decoding completes.
                </p>
                <Button disabled={!modelId || !datasetId || runMutation.isPending} onClick={() => runMutation.mutate()}>
                  <Play className="h-4 w-4" /> {runMutation.isPending ? 'Running…' : 'Run Evaluation'}
                </Button>
                {runMutation.error && <p className="text-sm text-rose-700">{(runMutation.error as Error).message}</p>}
                <Button variant="secondary" onClick={() => setStep(2)}>Back</Button>
              </CardContent>
            </Card>
          )}

          {step === 4 && results && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex flex-wrap items-center gap-2">
                    5. Results
                    <Badge variant={results.run.provenance === 'real' ? 'default' : 'secondary'}>
                      {results.run.provenance === 'real' ? <Users className="h-3 w-3 mr-1" /> : <FlaskConical className="h-3 w-3 mr-1" />}
                      {provenanceBadge}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="mb-6 rounded-xl border-2 border-indigo-100 bg-indigo-50/50 p-6 text-center">
                    <p className="text-xs font-medium uppercase tracking-wide text-indigo-700">Word Error Rate (sign gloss tokens)</p>
                    <p className="mt-2 text-5xl font-semibold text-indigo-950">{(results.aggregate.word_error_rate as number).toFixed(3)}</p>
                    <p className="mt-2 text-sm text-indigo-800">
                      Exact sequence accuracy {(results.aggregate.exact_sequence_accuracy as number * 100).toFixed(1)}%
                      · Mean latency {(results.aggregate.mean_inference_ms as number).toFixed(1)} ms
                    </p>
                  </div>

                  <div className="grid gap-3 md:grid-cols-4 text-sm mb-4">
                    <div className="rounded-lg border p-3"><p className="text-xs text-[var(--color-muted)]">Insertions</p><p className="text-lg font-medium">{results.aggregate.total_insertions}</p></div>
                    <div className="rounded-lg border p-3"><p className="text-xs text-[var(--color-muted)]">Deletions</p><p className="text-lg font-medium">{results.aggregate.total_deletions}</p></div>
                    <div className="rounded-lg border p-3"><p className="text-xs text-[var(--color-muted)]">Substitutions</p><p className="text-lg font-medium">{results.aggregate.total_substitutions}</p></div>
                    <div className="rounded-lg border p-3"><p className="text-xs text-[var(--color-muted)]">High uncertainty</p><p className="text-lg font-medium">{results.aggregate.high_uncertainty_count}</p></div>
                  </div>

                  {results.emotion.available ? (
                    <div className="rounded-lg border p-4 text-sm mb-4">
                      <p className="font-medium">Emotion metrics</p>
                      <p className="text-xs text-[var(--color-muted)] mt-1">
                        Accuracy {(results.emotion.accuracy as number * 100).toFixed(1)}%
                        · F1 {(results.emotion.f1 as number).toFixed(3)}
                        · Precision {(results.emotion.precision as number).toFixed(3)}
                        · Recall {(results.emotion.recall as number).toFixed(3)}
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-[var(--color-muted)] mb-4">{results.emotion.reason as string ?? 'Emotion metrics unavailable — no ground-truth labels in this split.'}</p>
                  )}

                  <div className="flex flex-wrap gap-2 mb-3">
                    {['all', 'correct', 'incorrect', 'uncertain', 'emotion'].map((f) => (
                      <button key={f} type="button" className={`rounded-full border px-3 py-1 text-xs ${filter === f ? 'bg-slate-900 text-white' : 'bg-white'}`} onClick={() => setFilter(f)}>
                        {f}
                      </button>
                    ))}
                  </div>

                  <div className="overflow-x-auto rounded-lg border">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50 text-left">
                        <tr>
                          <th className="p-2">Recording</th>
                          <th className="p-2">Signer</th>
                          <th className="p-2">Reference</th>
                          <th className="p-2">Predicted</th>
                          <th className="p-2">WER</th>
                          <th className="p-2">Match</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredPredictions.map((p) => (
                          <tr key={p.recording_id} className="border-t hover:bg-slate-50 cursor-pointer" onClick={() => setSelectedPred(p)}>
                            <td className="p-2 font-mono">{p.recording_id}</td>
                            <td className="p-2">{p.signer_id}</td>
                            <td className="p-2">{p.reference_signs.join('|')}</td>
                            <td className="p-2">{p.predicted_signs.join('|')}</td>
                            <td className="p-2">{p.word_error_rate.toFixed(2)}</td>
                            <td className="p-2">{p.exact_match ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {selectedPred && results.run.dataset_id && (
                    <Card className="mt-4">
                      <CardHeader><CardTitle>Recording detail — {selectedPred.recording_id}</CardTitle></CardHeader>
                      <CardContent>
                        <PredictionDetail row={selectedPred} datasetId={results.run.dataset_id} />
                      </CardContent>
                    </Card>
                  )}

                  <ul className="mt-4 text-xs text-[var(--color-muted)] list-disc pl-4">
                    {results.limitations.map((l) => <li key={l}>{l}</li>)}
                  </ul>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="history">
          <div className="space-y-3">
            {runs.length === 0 ? (
              <p className="text-sm text-[var(--color-muted)]">No evaluation runs yet.</p>
            ) : (
              runs.map((run) => (
                <div key={run.id} className="rounded-xl border bg-white p-4 text-sm flex flex-wrap justify-between gap-2">
                  <div>
                    <p className="font-medium flex items-center gap-2">
                      {run.name}
                      <Badge variant={run.provenance === 'real' ? 'default' : 'secondary'}>{run.provenance}</Badge>
                    </p>
                    <p className="text-xs text-[var(--color-muted)]">{run.summary}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs">WER {run.word_error_rate?.toFixed(3) ?? '—'}</span>
                    <Button size="sm" variant="secondary" onClick={() => { setActiveRunId(run.id); setStep(4) }}>View</Button>
                    <input type="checkbox" checked={compareIds.includes(run.id)} onChange={(e) => {
                      setCompareIds((prev) => e.target.checked ? [...prev, run.id] : prev.filter((id) => id !== run.id))
                    }} />
                  </div>
                </div>
              ))
            )}
            {compareIds.length >= 2 && (
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2"><BarChart3 className="h-4 w-4" /> Compare runs</CardTitle></CardHeader>
                <CardContent className="text-sm">
                  <CompareBlock ids={compareIds} />
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function CompareBlock({ ids }: { ids: number[] }) {
  const { data } = useQuery({
    queryKey: ['eval-compare', ids],
    queryFn: () => evaluationApi.compare(ids),
  })
  if (!data) return <p className="text-xs text-[var(--color-muted)]">Loading comparison…</p>
  return (
    <div className="space-y-2">
      {data.runs.map((r) => (
        <p key={r.id}>{r.name}: WER {r.word_error_rate?.toFixed(3)} · Acc {((r.sequence_accuracy ?? 0) * 100).toFixed(1)}%</p>
      ))}
    </div>
  )
}
