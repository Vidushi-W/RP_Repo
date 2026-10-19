import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { datasetApi } from '@/services/datasetApi'

export function DatasetDetailPage() {
  const { datasetId } = useParams()
  const id = Number(datasetId)
  const qc = useQueryClient()

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

  if (!dataset) return <p className="text-sm text-[var(--color-muted)]">Loading dataset…</p>

  return (
    <div>
      <PageHeader
        title={dataset.name}
        description={dataset.description || 'Dataset detail, recordings, splits, and validation.'}
        action={<Button variant="secondary" onClick={() => refetchValidation()}>Run Validation</Button>}
      />

      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <Badge variant="secondary">v{dataset.current_version}</Badge>
        <Badge variant="secondary">{dataset.provenance}</Badge>
        <Badge variant={dataset.status === 'ready' ? 'success' : 'secondary'}>{dataset.status}</Badge>
        <span className="text-[var(--color-muted)]">{dataset.recording_count} recordings</span>
      </div>

      <Tabs defaultValue="recordings">
        <TabsList>
          <TabsTrigger value="recordings">Recordings</TabsTrigger>
          <TabsTrigger value="splits">Splits</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
        </TabsList>

        <TabsContent value="recordings">
          <div className="overflow-hidden rounded-xl border border-[var(--color-border)] bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-[var(--color-muted)]">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Gloss sequence</th>
                  <th className="px-4 py-3">Emotion</th>
                  <th className="px-4 py-3">Split</th>
                  <th className="px-4 py-3">Duration</th>
                </tr>
              </thead>
              <tbody>
                {recordings.map((r) => (
                  <tr key={r.recording_id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3">
                      <Link className="font-medium text-indigo-700 hover:underline" to={`/datasets/${id}/recordings/${r.recording_id}`}>
                        {r.recording_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">{r.ordered_sign_labels || '—'}</td>
                    <td className="px-4 py-3 capitalize">{r.emotion_label}</td>
                    <td className="px-4 py-3">{r.split}</td>
                    <td className="px-4 py-3">{(r.duration_ms / 1000).toFixed(2)} s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="splits">
          <div className="rounded-xl border border-[var(--color-border)] bg-white p-5 text-sm">
            <p className="text-[var(--color-muted)]">Assign train / validation / test splits by recording group. Default ratio 70/15/15. Existing imported splits are preserved.</p>
            <p className="mt-2 text-xs text-amber-800">Synthetic signer IDs (e.g. SYNTHETIC_SIGNER_01) are artificial identifiers, not human participants.</p>
            <Button className="mt-4" variant="secondary" onClick={() => splitMutation.mutate()} disabled={splitMutation.isPending}>
              Apply 70/15/15 Split
            </Button>
            {splitMutation.data && (
              <pre className="mt-4 rounded-lg bg-slate-50 p-3 text-xs">{JSON.stringify(splitMutation.data, null, 2)}</pre>
            )}
          </div>
        </TabsContent>

        <TabsContent value="validation">
          {validation ? (
            <div className="rounded-xl border border-[var(--color-border)] bg-white p-5 text-sm space-y-2">
              <p>Valid: {validation.valid_recordings} · Invalid: {validation.invalid_recordings}</p>
              <p>Split counts: {JSON.stringify(validation.split_counts)}</p>
              {validation.split_isolation_errors.map((e) => <p key={e} className="text-rose-700">{e}</p>)}
              {validation.issues.map((e) => <p key={e} className="text-amber-800">{e}</p>)}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-muted)]">Run validation to see the dataset report.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
