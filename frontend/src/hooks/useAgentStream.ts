import { useEffect, useState } from 'react'
import type { AgentEvent } from '../types/agent'

/** Subscribes to the backend's SSE stream. `statusTick` increments whenever the session status/step changes. */
export function useAgentStream(sessionId: string | undefined) {
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [statusTick, setStatusTick] = useState(0)

  useEffect(() => {
    if (!sessionId) return
    setEvents([])
    const source = new EventSource(`${import.meta.env.VITE_API_URL ?? ''}/api/shopping/${sessionId}/events`)
    source.addEventListener('activity', (e) => {
      const event = JSON.parse((e as MessageEvent).data) as AgentEvent
      setEvents((prev) => (prev.some((p) => p.id === event.id) ? prev : [...prev, event]))
    })
    source.addEventListener('status', () => setStatusTick((t) => t + 1))
    return () => source.close()
  }, [sessionId])

  return { events, statusTick }
}
