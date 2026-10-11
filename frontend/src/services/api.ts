import axios from 'axios'

// In dev, Vite proxies /api and /store to the FastAPI backend. Set VITE_API_URL when hosting separately.
export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '' })

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (err.code === 'ERR_NETWORK') return 'Cannot reach the CartMind server. Is the backend running?'
    return err.message
  }
  return err instanceof Error ? err.message : 'Something went wrong'
}
