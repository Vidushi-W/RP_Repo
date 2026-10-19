import type { DictionaryResponse, LiveTickResponse, PlaygroundStatus, RecognitionMessage } from '@/types/playground'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new Error(await res.text() || `Error ${res.status}`)
  return res.json() as Promise<T>
}

export const playgroundApi = {
  status: () => request<PlaygroundStatus>('/playground/status'),
  recognize: async (file: File, modelId?: number) => {
    const form = new FormData()
    form.append('file', file)
    if (modelId) form.append('model_id', String(modelId))
    const res = await fetch('/api/playground/recognize', { method: 'POST', body: form })
    if (!res.ok) throw new Error(await res.text() || `Error ${res.status}`)
    return res.json() as Promise<RecognitionMessage>
  },
  dictionary: (modelId?: number) =>
    request<DictionaryResponse>(`/playground/dictionary${modelId ? `?model_id=${modelId}` : ''}`),
  history: () => request<RecognitionMessage[]>('/playground/history'),
  clearHistory: () => request<{ cleared: number }>('/playground/history', { method: 'DELETE' }),
  createLiveSession: (sourceType: string) =>
    request<{ session_id: string; source_type: string }>('/playground/live/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type: sourceType }),
    }),
  liveUpload: async (sessionId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`/api/playground/live/session/${sessionId}/upload`, { method: 'POST', body: form })
    if (!res.ok) throw new Error(await res.text())
    return res.json() as Promise<{ filename: string; frame_count: number; duration_ms: number }>
  },
  liveStart: (sessionId: string) => request<{ status: string }>(`/playground/live/session/${sessionId}/start`, { method: 'POST' }),
  livePause: (sessionId: string) => request<{ status: string }>(`/playground/live/session/${sessionId}/pause`, { method: 'POST' }),
  liveResume: (sessionId: string) => request<{ status: string }>(`/playground/live/session/${sessionId}/resume`, { method: 'POST' }),
  liveStop: (sessionId: string) => request<{ status: string }>(`/playground/live/session/${sessionId}/stop`, { method: 'POST' }),
  liveReset: (sessionId: string) => request<{ status: string }>(`/playground/live/session/${sessionId}/reset`, { method: 'POST' }),
  liveSpeed: (sessionId: string, speed: number) =>
    request<{ speed: number }>(`/playground/live/session/${sessionId}/speed`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ speed }),
    }),
  liveTick: (sessionId: string) => request<LiveTickResponse>(`/playground/live/session/${sessionId}/tick`),
  liveFinalize: (sessionId: string) =>
    request<{ message: Record<string, unknown> }>(`/playground/live/session/${sessionId}/finalize`, { method: 'POST' }),
}
