export interface StudioSettings {
  default_model_id: number | null
  torch_threads: number
  max_upload_mb: number
  training_concurrency: number
  uncertainty_threshold: number
  theme: 'light' | 'dark'
  data_dir: string
  artifacts_dir: string
  database_url: string
  max_upload_bytes: number
  paths_readonly: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(await res.text() || `Error ${res.status}`)
  return res.json() as Promise<T>
}

export const settingsApi = {
  get: () => request<StudioSettings>('/settings'),
  update: (body: Partial<StudioSettings>) =>
    request<StudioSettings>('/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  exportMetadata: () => request<Record<string, unknown>>('/settings/export'),
}
