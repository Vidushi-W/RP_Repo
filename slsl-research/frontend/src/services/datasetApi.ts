import type {
  DatasetSummary,
  DatasetValidationReport,
  ImportJob,
  ImportPreviewItem,
  RecordingDetail,
  RecordingSummary,
} from '@/types/dataset'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const datasetApi = {
  list: () => request<DatasetSummary[]>('/datasets'),
  get: (id: number) => request<DatasetSummary>(`/datasets/${id}`),
  create: (body: { name: string; description?: string; provenance?: string }) =>
    request<DatasetSummary>('/datasets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  listRecordings: (id: number) => request<RecordingSummary[]>(`/datasets/${id}/recordings`),
  getRecording: (datasetId: number, recordingId: string) =>
    request<RecordingDetail>(`/datasets/${datasetId}/recordings/${recordingId}`),
  updateRecording: (datasetId: number, recordingId: string, body: Record<string, string>) =>
    request<RecordingSummary>(`/datasets/${datasetId}/recordings/${recordingId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  preview: (files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return request<ImportPreviewItem[]>('/datasets/preview', { method: 'POST', body: form })
  },
  import: (datasetId: number, files: File[], manifest?: File, bumpVersion = false) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    if (manifest) form.append('manifest', manifest)
    form.append('bump_version', String(bumpVersion))
    return request<Record<string, unknown>>(`/datasets/${datasetId}/import`, { method: 'POST', body: form })
  },
  assignSplits: (datasetId: number, body: { train_ratio: number; val_ratio: number; preserve_existing: boolean }) =>
    request<Record<string, number>>(`/datasets/${datasetId}/splits`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  validate: (datasetId: number) => request<DatasetValidationReport>(`/datasets/${datasetId}/validation`),
  generateSynthetic: (body: { name: string; description?: string; total_recordings?: number; seed?: number }) =>
    request<DatasetSummary>('/datasets/generate-synthetic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listImports: () => request<ImportJob[]>('/datasets/imports'),
}
