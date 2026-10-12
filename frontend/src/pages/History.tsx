import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Shell from '../components/Shell/Shell'
import StatusBadge from '../components/ui/StatusBadge'
import { errorMessage } from '../services/api'
import { groupByDate, useSessionPrefs } from '../services/sessionPrefs'
import { inr, listSessions } from '../services/shopping'
import { timeAgo } from '../services/time'
import type { SessionSummary } from '../types/shopping'

export default function History() {
  const [items, setItems] = useState<SessionSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const prefs = useSessionPrefs()

  useEffect(() => {
    listSessions().then(setItems).catch((e) => setError(errorMessage(e)))
  }, [])

  const groups = useMemo(() => groupByDate((items ?? []).filter((s) => !prefs.hidden.includes(s.id))), [items, prefs.hidden])

  return (
    <Shell title="All searches">
      <div className="flex-1 overflow-y-auto px-4 py-8 md:px-6">
        <div className="mx-auto w-full max-w-[720px] space-y-6">
          {error && <p className="text-rose-600">{error}</p>}
          {items && groups.length === 0 && <p className="text-zinc-500">No sessions yet. Start one from the home page.</p>}
          {groups.map((g) => (
            <section key={g.label}>
              <h2 className="mb-2 text-[12px] font-medium uppercase tracking-wider text-zinc-400">{g.label}</h2>
              <div className="space-y-2">
                {g.items.map((s) => (
                  <Link key={s.id} to={`/session/${s.id}`} className="block rounded-xl border border-zinc-200 p-4 transition hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/30">
                    <div className="flex items-start justify-between gap-4">
                      <p className="min-w-0 break-words text-sm font-medium text-zinc-900">{prefs.titles[s.id] ?? s.query}</p>
                      <StatusBadge status={s.status} />
                    </div>
                    <p className="mt-1 text-[13px] text-zinc-500">
                      {s.product_name ? `${s.product_name.slice(0, 60)} · ${inr(s.price)}` : 'No product selected'}
                      {s.created_at && ` · ${timeAgo(s.created_at)}`}
                    </p>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </Shell>
  )
}
