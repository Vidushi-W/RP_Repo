import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { PageHeader } from '@/components/layout/PageHeader'
import { SensorChart } from '@/components/shared/SensorChart'
import { Button } from '@/components/ui/button'
import { datasetApi } from '@/services/datasetApi'

export function RecordingInspectorPage() {
  const { datasetId, recordingId } = useParams()
  const id = Number(datasetId)
  const qc = useQueryClient()

  const { data } = useQuery({
    queryKey: ['recording', id, recordingId],
    queryFn: () => datasetApi.getRecording(id, recordingId!),
    enabled: !!id && !!recordingId,
  })

  const [labels, setLabels] = useState('')
  const [emotion, setEmotion] = useState('unknown')
  const [sentence, setSentence] = useState('')
  const [signer, setSigner] = useState('')
  const [provenance, setProvenance] = useState('synthetic')
  const [split, setSplit] = useState('unassigned')

  useEffect(() => {
    if (data) {
      setLabels(data.ordered_sign_labels)
      setEmotion(data.emotion_label)
      setSentence(data.reference_english_sentence)
      setSigner(data.signer_id)
      setProvenance(data.provenance)
      setSplit(data.split)
    }
  }, [data])

  const tokens = labels.split('|').map((t) => t.trim()).filter(Boolean)

  const saveMutation = useMutation({
    mutationFn: () =>
      datasetApi.updateRecording(id, recordingId!, {
        ordered_sign_labels: labels,
        emotion_label: emotion,
        reference_english_sentence: sentence,
        signer_id: signer,
        provenance,
        split,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recording', id, recordingId] }),
  })

  if (!data) return <p className="text-sm text-[var(--color-muted)]">Loading recording…</p>

  return (
    <div>
      <PageHeader
        title={data.recording_id}
        description={`${(data.duration_ms / 1000).toFixed(2)} s · ${data.frame_count} frames · ~${data.sample_rate_hz.toFixed(1)} Hz`}
        action={<Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>Save Annotation</Button>}
      />

      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <SensorChart title="Left-hand movement" series={data.visualization.left_motion} color="#4f46e5" />
        <SensorChart title="Right-hand movement" series={data.visualization.right_motion} color="#0891b2" />
        <SensorChart title="Left flex 1" series={data.visualization.left_flex_1} color="#7c3aed" />
        <SensorChart title="Right flex 1" series={data.visualization.right_flex_1} color="#db2777" />
      </div>

      <div className="rounded-xl border border-[var(--color-border)] bg-white p-5 space-y-4">
        <div>
          <label className="text-xs font-medium text-[var(--color-muted)]">Sign sequence (pipe-separated)</label>
          <input className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={labels} onChange={(e) => setLabels(e.target.value)} placeholder="I|NEED|WATER" />
          <div className="mt-2 flex flex-wrap gap-2">
            {tokens.map((t, i) => (
              <span key={`${t}-${i}`} className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">{t}</span>
            ))}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-xs font-medium text-[var(--color-muted)]">Emotion</label>
            <select className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={emotion} onChange={(e) => setEmotion(e.target.value)}>
              <option value="neutral">Neutral</option>
              <option value="angry">Angry</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--color-muted)]">Split</label>
            <select className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={split} onChange={(e) => setSplit(e.target.value)}>
              <option value="train">Train</option>
              <option value="val">Validation</option>
              <option value="test">Test</option>
              <option value="unassigned">Unassigned</option>
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs font-medium text-[var(--color-muted)]">Reference English sentence</label>
          <input className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={sentence} onChange={(e) => setSentence(e.target.value)} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="text-xs font-medium text-[var(--color-muted)]">Signer ID</label>
            <input className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={signer} onChange={(e) => setSigner(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--color-muted)]">Provenance</label>
            <select className="mt-1 w-full rounded-md border px-3 py-2 text-sm" value={provenance} onChange={(e) => setProvenance(e.target.value)}>
              <option value="synthetic">Synthetic</option>
              <option value="real">Real</option>
            </select>
          </div>
        </div>
        {data.validation.warnings.map((w) => <p key={w} className="text-xs text-amber-800">{w}</p>)}
      </div>
    </div>
  )
}
