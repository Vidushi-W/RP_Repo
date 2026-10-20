import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Alert } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { FileUploadZone } from '@/components/shared/FileUploadZone'
import { classifyImportFiles, datasetApi } from '@/services/datasetApi'
import type { ImportPreviewItem } from '@/types/dataset'

const STEPS = ['Select Files', 'Inspect Format', 'Import Labels', 'Validate', 'Review', 'Save Dataset']

interface ImportWizardProps {
  datasetId?: number
  datasetName?: string
  embedded?: boolean
  onClose: () => void
}

export function ImportWizard({ datasetId, datasetName: initialName, embedded = false, onClose }: ImportWizardProps) {
  const qc = useQueryClient()
  const [step, setStep] = useState(0)
  const [files, setFiles] = useState<File[]>([])
  const [manifest, setManifest] = useState<File | null>(null)
  const [previews, setPreviews] = useState<ImportPreviewItem[]>([])
  const [datasetName, setDatasetName] = useState(initialName ?? 'Imported Sensor Dataset')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const classified = useMemo(() => classifyImportFiles(files), [files])
  const effectiveManifest = manifest ?? classified.manifestInFiles

  const goBack = () => {
    setError(null)
    setStep((s) => Math.max(0, s - 1))
  }

  const previewMutation = useMutation({
    mutationFn: async () => {
      setError(null)
      if (!classified.payload.length) {
        throw new Error('Add at least one sensor CSV file or a dataset ZIP archive.')
      }
      if (classified.zips.length && !classified.sensorCsvs.length) {
        return [{
          filename: classified.zips[0].name,
          valid: true,
          errors: [],
          warnings: ['ZIP archive will be unpacked during import. Sensor format is validated after upload.'],
          frame_count: 0,
          duration_ms: 0,
        }] satisfies ImportPreviewItem[]
      }
      return datasetApi.preview(classified.sensorCsvs)
    },
    onSuccess: (data) => {
      setPreviews(data)
      setStep(1)
    },
    onError: (e: Error) => setError(e.message),
  })

  const importMutation = useMutation({
    mutationFn: async () => {
      setError(null)
      if (!classified.payload.length) {
        throw new Error('No importable files selected. Sensor CSVs or a ZIP archive is required.')
      }
      let id = datasetId
      if (!id) {
        const ds = await datasetApi.create({ name: datasetName.trim() || 'Imported Sensor Dataset', provenance: 'imported' })
        id = ds.id
      }
      const data = await datasetApi.import(id, classified.payload, effectiveManifest ?? undefined)
      if (data.imported === 0) {
        const detail = data.errors.length ? data.errors.join(' ') : 'No recordings were imported. Check the 23-column sensor CSV schema.'
        throw new Error(detail)
      }
      return { ...data, dataset_id: id }
    },
    onSuccess: (data) => {
      setResult(data)
      setStep(5)
      qc.invalidateQueries({ queryKey: ['datasets'] })
      qc.invalidateQueries({ queryKey: ['imports'] })
      if (datasetId) {
        qc.invalidateQueries({ queryKey: ['dataset', datasetId] })
        qc.invalidateQueries({ queryKey: ['recordings', datasetId] })
      }
      qc.invalidateQueries({ queryKey: ['system-status'] })
    },
    onError: (e: Error) => setError(e.message),
  })

  const resetToFileSelection = () => {
    setStep(0)
    setFiles([])
    setManifest(null)
    setPreviews([])
    setError(null)
    previewMutation.reset()
    importMutation.reset()
  }

  const validCount = previews.filter((p) => p.valid).length
  const busy = previewMutation.isPending || importMutation.isPending

  return (
    <div className={embedded ? '' : 'rounded-xl border border-border bg-surface p-6 shadow-sm'}>
      {!embedded && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">Import dataset</h3>
            <p className="text-xs text-muted">Step {step + 1} of {STEPS.length} — {STEPS[step]}</p>
          </div>
          {step < 5 && (
            <Button type="button" variant="secondary" size="sm" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
          )}
        </div>
      )}
      {embedded && (
        <p className="mb-4 text-xs text-muted">Step {step + 1} of {STEPS.length} — {STEPS[step]}</p>
      )}

      <div className="mb-6 flex flex-wrap gap-2">
        {STEPS.map((label, i) => (
          <span key={label} className={`rounded-full px-3 py-1 text-xs ${i === step ? 'bg-accent-soft text-accent font-medium' : i < step ? 'bg-border/60 text-foreground' : 'bg-surface-muted text-muted'}`}>
            {i + 1}. {label}
          </span>
        ))}
      </div>

      {step === 0 && (
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-muted)]">
            Upload 23-column sensor CSV files or a ZIP package. Labels belong in a separate manifest CSV, not inside sensor files.
          </p>
          <FileUploadZone
            files={files}
            onChange={(next) => { setFiles(next); setError(null) }}
            accept=".csv,.zip,text/csv,application/zip"
            hint="Required columns: timestamp_ms + 22 glove features (flex, acc, gyro per hand)."
          />
          {!datasetId && (
            <div className="space-y-1.5">
              <Label htmlFor="import-dataset-name">Dataset name</Label>
              <Input id="import-dataset-name" value={datasetName} onChange={(e) => setDatasetName(e.target.value)} placeholder="Imported Sensor Dataset" />
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button disabled={!files.length || busy} onClick={() => previewMutation.mutate()}>
              {previewMutation.isPending ? 'Inspecting…' : 'Inspect Format'}
            </Button>
            {files.length > 0 && (
              <Button type="button" variant="secondary" onClick={() => setFiles([])} disabled={busy}>
                Clear files
              </Button>
            )}
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-3">
          {previews.map((p) => (
            <div key={p.filename} className="rounded-lg border px-3 py-2 text-sm">
              <div className="flex justify-between"><span className="font-medium">{p.filename}</span><span className={p.valid ? 'text-emerald-700' : 'text-rose-700'}>{p.valid ? 'Valid' : 'Invalid'}</span></div>
              {p.frame_count > 0 && <p className="text-xs text-[var(--color-muted)]">{p.frame_count} frames · {(p.duration_ms / 1000).toFixed(2)} s</p>}
              {p.warnings.map((w) => <p key={w} className="text-xs text-amber-800">{w}</p>)}
              {p.errors.map((e) => <p key={e} className="text-xs text-rose-700">{e}</p>)}
            </div>
          ))}
          <div className="flex flex-wrap gap-2 pt-1">
            <Button variant="secondary" disabled={!validCount && !classified.zips.length} onClick={() => setStep(2)}>
              Continue to Labels
            </Button>
            <Button type="button" variant="secondary" onClick={resetToFileSelection}>
              Choose different files
            </Button>
            <Button type="button" variant="secondary" onClick={goBack}>
              Back
            </Button>
          </div>
          {!validCount && !classified.zips.length && (
            <p className="text-xs text-rose-700">Files failed validation. Use &quot;Choose different files&quot; to upload again.</p>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-muted)]">Optional manifest with recording_id, ordered_sign_labels, emotion_label, split, and related metadata.</p>
          {effectiveManifest && <p className="text-xs text-emerald-700">Using manifest from upload: {effectiveManifest.name}</p>}
          <FileUploadZone
            files={manifest ? [manifest] : []}
            onChange={(next) => setManifest(next[0] ?? null)}
            accept=".csv,text/csv"
            multiple={false}
            label="Choose manifest CSV"
            hint="manifest.csv is optional if you will annotate recordings later."
          />
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setStep(3)}>Continue</Button>
            <Button type="button" variant="secondary" onClick={goBack}>Back</Button>
            <Button type="button" variant="secondary" onClick={resetToFileSelection}>Start over</Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3 text-sm">
          <p>{validCount || classified.zips.length} file(s) ready to import.</p>
          <p className="text-[var(--color-muted)]">Manifest: {effectiveManifest?.name ?? 'none — annotations can be added later'}</p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setStep(4)}>Review</Button>
            <Button type="button" variant="secondary" onClick={goBack}>Back</Button>
            <Button type="button" variant="secondary" onClick={resetToFileSelection}>Start over</Button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-4 text-sm">
          <p>Import {classified.payload.length} file(s) into {datasetId ? initialName ?? 'this dataset' : datasetName}.</p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => importMutation.mutate()} disabled={busy}>
              {importMutation.isPending ? 'Importing…' : 'Save Dataset'}
            </Button>
            <Button type="button" variant="secondary" onClick={goBack} disabled={busy}>Back</Button>
            <Button type="button" variant="secondary" onClick={resetToFileSelection} disabled={busy}>Start over</Button>
          </div>
        </div>
      )}

      {step === 5 && result && (
        <div className="space-y-2 text-sm">
          <p className="font-medium text-emerald-700">Import completed — {String(result.imported)} recording(s) added.</p>
          <pre className="rounded-lg bg-slate-50 p-3 text-xs">{JSON.stringify(result, null, 2)}</pre>
          <Button onClick={onClose}>Close</Button>
        </div>
      )}

      {error && <Alert variant="danger" className="mt-4">{error}</Alert>}
    </div>
  )
}
