/* apps/dashboard/src/hooks/useApi.ts — typed API helpers */
import { useQuery } from '@tanstack/react-query';

const BASE = '';  // proxied to :8002

export function useCalls(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['calls', limit, offset],
    queryFn: () => fetch(`${BASE}/calls?limit=${limit}&offset=${offset}`).then(r => r.json()),
  });
}

export function useOperatorStats() {
  return useQuery({
    queryKey: ['operator-stats'],
    queryFn: () => fetch(`${BASE}/operators/stats`).then(r => r.json()),
  });
}

export function useFlagged() {
  return useQuery({
    queryKey: ['flagged'],
    queryFn: () => fetch(`${BASE}/flagged`).then(r => r.json()),
  });
}

export function useCompliance() {
  return useQuery({
    queryKey: ['compliance'],
    queryFn: () => fetch(`${BASE}/compliance`).then(r => r.json()),
  });
}
