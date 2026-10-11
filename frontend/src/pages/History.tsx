import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Shell from '../components/Shell/Shell'
import { errorMessage } from '../services/api'
import { inr, listSessions } from '../services/shopping'
import { timeAgo } from '../services/time'
import type { SessionStatus, SessionSummary } from '../types/shopping'

const LABEL: Record<SessionStatus, { text: string; cls: string }> = {
  started: { text: 'Starting', cls: 'bg-blue-50 text-blue-700' },
  running: { text: 'Working', cls: 'bg-blue-50 text-blue-700' },
  waiting_for_approval: { text: 'Needs approval', cls: 'bg-amber-50 text-amber-700' },
  executing: { text: 'Shopping', cls: 'bg-blue-50 text-blue-700' },
  waiting_for_user: { text: 'Needs you', cls: 'bg-amber-50 text-amber-700' },
  price_changed: { text: 'Price changed', cls: 'bg-amber-50 text-amber-700' },
  completed: { text: 'In cart', cls: 'bg-emerald-50 text-emerald-700' },
  cancelled: { text: 'Cancelled', cls: 'bg-zinc-100 text-zinc-600' },
  failed: { text: 'Failed', cls: 'bg-rose-50 text-rose-700' },
  no_results: { text: 'No match', cls: 'bg-rose-50 text-rose-700' },
  needs_clarification: { text: 'Needs info', cls: 'bg-amber-50 text-amber-700' },
}

export default function History() {
  const [items, setItems] = useState<SessionSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listSessions().then(setItems).catch((e) => setError(errorMessage(e)))
  }, [])

  return (
    <Shell>
      <div className="flex-1 overflow-y-auto px-4 py-8">
        <div className="mx-auto w-full max-w-[640px] space-y-3">
          <h1 className="text-xl font-semibold">Shopping history</h1>
          {error && <p className="text-rose-600">{error}</p>}
          {items?.length === 0 && <p className="text-zinc-500">No sessions yet. Start one from the home page.</p>}
          {items?.map((s) => {
            const label = LABEL[s.status] ?? { text: s.status, cls: 'bg-zinc-100 text-zinc-600' }
            return (
              <Link key={s.id} to={`/session/${s.id}`} className="block rounded-xl border border-zinc-200 p-4 transition hover:bg-zinc-50">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm font-medium text-zinc-900">{s.query}</p>
                  <span className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-medium ${label.cls}`}>{label.text}</span>
                </div>
                <p className="mt-1 text-[13px] text-zinc-500">
                  {s.product_name ? `${s.product_name.slice(0, 60)} · ${inr(s.price)}` : 'No product selected'}
                  {s.created_at && ` · ${timeAgo(s.created_at)}`}
                </p>
              </Link>
            )
          })}
        </div>
      </div>
    </Shell>
  )
}
