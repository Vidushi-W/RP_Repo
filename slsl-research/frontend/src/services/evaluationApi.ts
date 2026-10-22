import type { EvalCompatibility, EvaluationResults, EvaluationRun, StartEvaluationPayload } from '@/types/evaluation'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Error ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const evaluationApi = {
  preview: (modelId: number, datasetId: number, split = 'test') =>
    request<EvalCompatibility>(`/evaluation/preview?model_id=${modelId}&dataset_id=${datasetId}&split=${split}`),
  run: (body: StartEvaluationPayload) =>
    request<EvaluationRun>('/evaluation/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listRuns: (provenance?: string) =>
    request<EvaluationRun[]>(`/evaluation/runs${provenance ? `?provenance=${provenance}` : ''}`),
  getRun: (id: number) => request<EvaluationRun>(`/evaluation/runs/${id}`),
  getResults: (id: number) => request<EvaluationResults>(`/evaluation/runs/${id}/results`),
  compare: (ids: number[]) => request<{ runs: EvaluationRun[]; comparison: Record<string, unknown> }>(`/evaluation/compare?ids=${ids.join(',')}`),
}
