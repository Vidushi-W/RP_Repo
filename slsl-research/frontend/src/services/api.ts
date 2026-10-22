import type { HealthResponse, SystemStatus } from '@/types/system'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`)
  if (!res.ok) {
    throw new Error(`API error ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<HealthResponse>('/health'),
  systemStatus: () => get<SystemStatus>('/system/status'),
}
