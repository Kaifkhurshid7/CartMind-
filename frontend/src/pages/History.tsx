import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { errorMessage } from '../services/api'
import { inr, listSessions } from '../services/shopping'
import type { SessionStatus, SessionSummary } from '../types/shopping'

const LABEL: Record<SessionStatus, { text: string; cls: string }> = {
  started: { text: 'Starting', cls: 'text-brand-400' },
  running: { text: 'Working', cls: 'text-brand-400' },
  waiting_for_approval: { text: 'Needs approval', cls: 'text-amber-300' },
  executing: { text: 'Shopping', cls: 'text-brand-400' },
  price_changed: { text: 'Price changed', cls: 'text-amber-300' },
  completed: { text: 'In cart', cls: 'text-emerald-400' },
  cancelled: { text: 'Cancelled', cls: 'text-slate-400' },
  failed: { text: 'Failed', cls: 'text-rose-400' },
  no_results: { text: 'No match', cls: 'text-rose-300' },
  needs_clarification: { text: 'Needs info', cls: 'text-amber-300' },
}

export default function History() {
  const [items, setItems] = useState<SessionSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listSessions().then(setItems).catch((e) => setError(errorMessage(e)))
  }, [])

  return (
    <div className="mx-auto max-w-3xl space-y-3">
      <h1 className="text-2xl font-bold text-white">Shopping history</h1>
      {error && <p className="text-rose-400">{error}</p>}
      {items?.length === 0 && <p className="text-slate-400">No sessions yet. Start one from the home page.</p>}
      {items?.map((s) => {
        const label = LABEL[s.status] ?? { text: s.status, cls: 'text-slate-400' }
        return (
          <Link key={s.id} to={`/session/${s.id}`} className="card block transition hover:border-brand-500/50">
            <div className="flex items-start justify-between gap-4">
              <p className="font-medium text-white">{s.query}</p>
              <span className={`shrink-0 text-xs font-semibold ${label.cls}`}>{label.text}</span>
            </div>
            <p className="mt-1 text-sm text-slate-400">
              {s.product_name ? `${s.product_name} · ${inr(s.price)}` : 'No product selected'}
              {s.created_at && ` · ${new Date(s.created_at).toLocaleString()}`}
            </p>
          </Link>
        )
      })}
    </div>
  )
}
