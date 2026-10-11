import { useEffect, useRef } from 'react'
import type { AgentEvent } from '../../types/agent'
import type { SessionStatus } from '../../types/shopping'

const ICON: Record<string, { glyph: string; cls: string }> = {
  done: { glyph: '✓', cls: 'text-emerald-400' },
  error: { glyph: '✕', cls: 'text-rose-400' },
  waiting: { glyph: '⏳', cls: 'text-amber-300' },
  running: { glyph: '●', cls: 'text-brand-400' },
}

export default function AgentActivity({ events, status }: { events: AgentEvent[]; status?: SessionStatus }) {
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => endRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), [events.length])

  const working = status === 'running' || status === 'started' || status === 'executing'

  return (
    <section className="card" aria-label="Agent activity">
      <header className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Agent Activity</h2>
        {working && <span className="chip animate-pulse text-brand-400">working…</span>}
      </header>
      <ol className="max-h-72 space-y-1.5 overflow-y-auto pr-1 text-sm">
        {events.length === 0 && <li className="text-slate-500">Waiting for the agent to start…</li>}
        {events.map((e, i) => {
          // An old "waiting" entry is resolved as soon as anything newer arrives.
          const resolved = e.status === 'waiting' && i < events.length - 1
          const icon = ICON[resolved ? 'done' : e.status] ?? ICON.done
          return (
            <li key={e.id} className="flex gap-2">
              <span className={`w-4 shrink-0 text-center ${icon.cls}`}>{icon.glyph}</span>
              <span className={e.status === 'error' ? 'text-rose-300' : 'text-slate-300'}>{e.message}</span>
            </li>
          )
        })}
        <div ref={endRef} />
      </ol>
    </section>
  )
}
