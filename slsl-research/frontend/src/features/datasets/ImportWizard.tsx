import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { datasetApi } from '@/services/datasetApi'
import type { ImportPreviewItem } from '@/types/dataset'

const STEPS = ['Select Files', 'Inspect Format', 'Import Labels', 'Validate', 'Review', 'Save Dataset']

interface ImportWizardProps {
  datasetId?: number
  onClose: () => void
}

export function ImportWizard({ datasetId, onClose }: ImportWizardProps) {
  const qc = useQueryClient()
  const [step, setStep] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [manifest, setManifest] = useState<File | null>(null)
  const [previews, setPreviews] = useState<ImportPreviewItem[]>([])
  const [datasetName, setDatasetName] = useState('Imported Sensor Dataset')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const previewMutation = useMutation({
    mutationFn: () => datasetApi.preview(files),
    onSuccess: (data) => { setPreviews(data); setStep(1) },
    onError: (e: Error) => setError(e.message),
  })

  const importMutation = useMutation({
    mutationFn: async () => {
      let id = datasetId
      if (!id) {
        const ds = await datasetApi.create({ name: datasetName, provenance: 'imported' })
        id = ds.id
      }
      const csvs = files.filter((f) => f.name.toLowerCase().endsWith('.csv') && f.name.toLowerCase() !== 'manifest.csv')
      const zips = files.filter((f) => f.name.toLowerCase().endsWith('.zip'))
      const payload = zips.length ? zips : csvs
      return datasetApi.import(id!, payload, manifest ?? undefined)
    },
    onSuccess: (data) => {
      setResult(data)
      setStep(5)
      qc.invalidateQueries({ queryKey: ['datasets'] })
      qc.invalidateQueries({ queryKey: ['system-status'] })
    },
    onError: (e: Error) => setError(e.message),
  })

  return (
    <div className="rounded-xl border border-[var(--color-border)] bg-white p-6">
      <div className="mb-6 flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <span key={label} className={`rounded-full px-3 py-1 text-xs ${i === step ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-[var(--color-muted)]'}`}>
            {i + 1}. {label}
          </span>
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-muted)]">Upload sensor CSV files, a dataset ZIP, and optionally a separate manifest CSV.</p>
          <input type="file" multiple accept=".csv,.zip" onChange={(e) => setFiles(Array.from(e.target.files ?? []))} />
          {!datasetId && (
            <input className="w-full rounded-md border px-3 py-2 text-sm" value={datasetName} onChange={(e) => setDatasetName(e.target.value)} placeholder="Dataset name" />
          )}
          <Button disabled={!files.length} onClick={() => previewMutation.mutate()}>Inspect Format</Button>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          {previews.map((p) => (
            <div key={p.filename} className="rounded-lg border px-3 py-2 text-sm">
              <div className="flex justify-between"><span className="font-medium">{p.filename}</span><span>{p.valid ? 'Valid' : 'Invalid'}</span></div>
              <p className="text-xs text-[var(--color-muted)]">{p.frame_count} frames · {(p.duration_ms / 1000).toFixed(2)} s</p>
              {p.errors.map((e) => <p key={e} className="text-xs text-rose-700">{e}</p>)}
            </div>
          ))}
          <Button variant="secondary" onClick={() => setStep(2)}>Continue to Labels</Button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-muted)]">Optional manifest with recording_id, ordered_sign_labels, emotion_label, split, and related metadata.</p>
          <input type="file" accept=".csv" onChange={(e) => setManifest(e.target.files?.[0] ?? null)} />
          <Button variant="secondary" onClick={() => setStep(3)}>Continue</Button>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3 text-sm">
          <p>{previews.filter((p) => p.valid).length} valid sensor files ready.</p>
          <p className="text-[var(--color-muted)]">Manifest: {manifest?.name ?? 'none — annotations can be added later'}</p>
          <Button onClick={() => setStep(4)}>Review</Button>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-4 text-sm">
          <p>Import {files.length} file(s) into {datasetName}.</p>
          <Button onClick={() => importMutation.mutate()} disabled={importMutation.isPending}>Save Dataset</Button>
        </div>
      )}

      {step === 5 && result && (
        <div className="space-y-2 text-sm">
          <p className="font-medium text-emerald-700">Import completed.</p>
          <pre className="rounded-lg bg-slate-50 p-3 text-xs">{JSON.stringify(result, null, 2)}</pre>
          <Button onClick={onClose}>Close</Button>
        </div>
      )}

      {error && <p className="mt-4 text-sm text-rose-700">{error}</p>}
    </div>
  )
}
