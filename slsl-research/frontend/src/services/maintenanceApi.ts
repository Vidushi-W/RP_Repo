export interface StorageSummary {
  database_path: string
  database_size_bytes: number
  data_dir: string
  data_dir_size_bytes: number
  artifacts_dir: string
  artifacts_dir_size_bytes: number
  counts: Record<string, number>
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(await res.text() || `Error ${res.status}`)
  return res.json() as Promise<T>
}

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

export const maintenanceApi = {
  storage: () => request<StorageSummary>('/maintenance/storage'),
  formatBytes,
  deleteDataset: (id: number, confirmation: string, force = false) =>
    request<{ dataset_id: number }>(`/maintenance/datasets/${id}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation, force }),
    }),
  deleteRecording: (datasetId: number, recordingId: string) =>
    request(`/maintenance/datasets/${datasetId}/recordings/${recordingId}`, { method: 'DELETE' }),
  deleteJob: (jobId: number) => request(`/maintenance/training/jobs/${jobId}`, { method: 'DELETE' }),
  deleteEvaluation: (runId: number) => request(`/maintenance/evaluations/${runId}`, { method: 'DELETE' }),
  deleteModel: (modelId: number, confirmation: string) =>
    request(`/maintenance/models/${modelId}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirmation }),
    }),
  clearRecognitionHistory: () => request<{ cleared: number }>('/maintenance/recognition-history', { method: 'DELETE' }),
  clearEvaluations: () => request<{ cleared: number }>('/maintenance/evaluations', { method: 'DELETE' }),
  resetDatabase: (scope: 'training' | 'synthetic' | 'all', confirmation: string, deleteFiles = false) =>
    request('/maintenance/reset-database', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, confirmation, delete_files: deleteFiles }),
    }),
}
