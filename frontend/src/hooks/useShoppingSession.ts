import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../services/api'
import { getSession } from '../services/shopping'
import type { ShoppingSession } from '../types/shopping'
import { useAgentStream } from './useAgentStream'

const BUSY = new Set(['started', 'running', 'executing'])

export function useShoppingSession(sessionId: string | undefined) {
  const [session, setSession] = useState<ShoppingSession | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { events, statusTick } = useAgentStream(sessionId)
  const alive = useRef(true)

  const refresh = useCallback(async () => {
    if (!sessionId) return
    try {
      const data = await getSession(sessionId)
      if (alive.current) {
        setSession(data)
        setError(null)
      }
    } catch (err) {
      if (alive.current) setError(errorMessage(err))
    }
  }, [sessionId])

  useEffect(() => {
    alive.current = true
    refresh()
    return () => {
      alive.current = false
    }
  }, [refresh, statusTick])

  // Safety net in case the SSE connection drops while the agent is working.
  useEffect(() => {
    if (!session || !BUSY.has(session.status)) return
    const t = setInterval(refresh, 3000)
    return () => clearInterval(t)
  }, [session, refresh])

  return { session, events, error, refresh, busy: !!session && BUSY.has(session.status) }
}
