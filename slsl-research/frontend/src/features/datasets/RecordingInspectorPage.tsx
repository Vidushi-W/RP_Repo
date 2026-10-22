import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/layout/PageHeader'
import { LoadingSpinner } from '@/components/shared/LoadingState'
import { SensorChart } from '@/components/shared/SensorChart'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { datasetApi } from '@/services/datasetApi'
import { maintenanceApi } from '@/services/maintenanceApi'

export function RecordingInspectorPage() {
  const { datasetId, recordingId } = useParams()
  const id = Number(datasetId)
  const qc = useQueryClient()
  const navigate = useNavigate()

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

  const deleteMutation = useMutation({
    mutationFn: () => maintenanceApi.deleteRecording(id, recordingId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['recordings', id] })
      qc.invalidateQueries({ queryKey: ['dataset', id] })
      navigate(`/datasets/${id}`)
    },
  })

  const canDelete = data && (data.provenance === 'synthetic' || !data.validation.warnings.some((w) => w.includes('protected')))

  if (!data) return <LoadingSpinner label="Loading recording…" className="py-12" />

  return (
    <div>
      <PageHeader
        title={data.recording_id}
        description={`${(data.duration_ms / 1000).toFixed(2)} s · ${data.frame_count} frames · ~${data.sample_rate_hz.toFixed(1)} Hz`}
        breadcrumbs={[
          { label: 'Datasets', href: '/datasets' },
          { label: `Dataset ${id}`, href: `/datasets/${id}` },
          { label: data.recording_id },
        ]}
        action={<Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>Save Annotation</Button>}
      />

      <div className="mb-6 grid gap-4 lg:grid-cols-2">
        <SensorChart title="Left-hand movement" series={data.visualization.left_motion} color="#4f46e5" />
        <SensorChart title="Right-hand movement" series={data.visualization.right_motion} color="#0891b2" />
        <SensorChart title="Left flex 1" series={data.visualization.left_flex_1} color="#7c3aed" />
        <SensorChart title="Right flex 1" series={data.visualization.right_flex_1} color="#db2777" />
      </div>

      <Card>
        <CardContent className="space-y-4 pt-5">
        <div>
          <Label>Sign sequence (pipe-separated)</Label>
          <Input className="mt-1.5" value={labels} onChange={(e) => setLabels(e.target.value)} placeholder="I|NEED|WATER" />
          <div className="mt-2 flex flex-wrap gap-2">
            {tokens.map((t, i) => (
              <span key={`${t}-${i}`} className="rounded-full bg-accent-soft px-3 py-1 text-xs font-medium text-accent">{t}</span>
            ))}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <Label>Emotion</Label>
            <Select className="mt-1.5" value={emotion} onChange={(e) => setEmotion(e.target.value)}>
              <option value="neutral">Neutral</option>
              <option value="angry">Angry</option>
              <option value="unknown">Unknown</option>
            </Select>
          </div>
          <div>
            <Label>Split</Label>
            <Select className="mt-1.5" value={split} onChange={(e) => setSplit(e.target.value)}>
              <option value="train">Train</option>
              <option value="val">Validation</option>
              <option value="test">Test</option>
              <option value="unassigned">Unassigned</option>
            </Select>
          </div>
        </div>
        <div>
          <Label>Reference English sentence</Label>
          <Input className="mt-1.5" value={sentence} onChange={(e) => setSentence(e.target.value)} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <Label>Signer ID</Label>
            <Input className="mt-1.5" value={signer} onChange={(e) => setSigner(e.target.value)} />
          </div>
          <div>
            <Label>Provenance</Label>
            <Select className="mt-1.5" value={provenance} onChange={(e) => setProvenance(e.target.value)}>
              <option value="synthetic">Synthetic</option>
              <option value="real">Real</option>
            </Select>
          </div>
        </div>
        {data.validation.warnings.map((w) => <Alert key={w} variant="warning">{w}</Alert>)}
        {canDelete ? (
          <div className="border-t pt-4">
            <Button variant="secondary" size="sm" disabled={deleteMutation.isPending} onClick={() => {
              if (window.confirm(`Delete recording ${recordingId}? This cannot be undone.`)) deleteMutation.mutate()
            }}>
              Delete recording
            </Button>
            {deleteMutation.error && <p className="mt-2 text-xs text-rose-700">{(deleteMutation.error as Error).message}</p>}
          </div>
        ) : (
          <p className="text-xs text-muted">Protected real recordings cannot be deleted individually. Delete the whole dataset from Settings or the dataset page.</p>
        )}
        </CardContent>
      </Card>
    </div>
  )
}
