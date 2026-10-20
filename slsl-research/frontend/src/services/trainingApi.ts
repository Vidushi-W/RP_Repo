import type { ModelRecord, StartTrainingPayload, TrainingJob, TrainingPreview } from '@/types/training'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(await res.text() || `Error ${res.status}`)
  return res.json() as Promise<T>
}

export const trainingApi = {
  preview: (datasetId: number) => request<TrainingPreview>(`/training/preview/${datasetId}`),
  start: (body: StartTrainingPayload) =>
    request<TrainingJob>('/training/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  listJobs: () => request<TrainingJob[]>('/training/jobs'),
  getJob: (id: number) => request<TrainingJob>(`/training/jobs/${id}`),
  cancelJob: (id: number) => request<TrainingJob>(`/training/jobs/${id}/cancel`, { method: 'POST' }),
  listModels: (includeArchived = false) => request<ModelRecord[]>(`/models?include_archived=${includeArchived}`),
  activateModel: (id: number) => request<ModelRecord>(`/models/${id}/activate`, { method: 'POST' }),
  archiveModel: (id: number) => request<ModelRecord>(`/models/${id}/archive`, { method: 'POST' }),
  resetPreview: (body: Record<string, boolean>) =>
    request<{
      active_models: { id: number; name: string }[]
      models_to_archive: { id: number; name: string }[]
      jobs_to_clear: { id: number; name: string; status: string }[]
      datasets_to_remove: { id: number; name: string }[]
      warnings: string[]
    }>('/training/reset/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  resetExecute: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>('/training/reset/execute', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  exportModel: async (id: number) => {
    const res = await fetch(`/api/models/${id}/export`)
    if (!res.ok) throw new Error(await res.text() || `Error ${res.status}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `slsl_model_${id}.zip`
    a.click()
    URL.revokeObjectURL(url)
  },
}
