import { useEffect, useState } from 'react'
import { api } from '../services/api'

export interface Health {
  llm_configured: boolean
  llm_model: string | null
  shopping_mode: 'live' | 'demo'
  site: string
}

export function useHealth() {
  const [health, setHealth] = useState<Health | null>(null)
  useEffect(() => {
    api.get<Health>('/api/health').then((r) => setHealth(r.data)).catch(() => setHealth(null))
  }, [])
  return health
}
