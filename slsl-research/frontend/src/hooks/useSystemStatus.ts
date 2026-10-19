import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: api.systemStatus,
    refetchInterval: 15000,
  })
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 15000,
  })
}
