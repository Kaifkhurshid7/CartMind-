import { useCallback, useEffect, useMemo, useState } from 'react'
import EmptyHistoryState, { HistorySkeleton } from '../components/History/EmptyHistoryState'
import HistoryCard from '../components/History/HistoryCard'
import HistoryToolbar, { SortKey } from '../components/History/HistoryToolbar'
import Shell from '../components/Shell/Shell'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import { statusInfo } from '../components/ui/StatusBadge'
import { errorMessage } from '../services/api'
import { groupByDate, hideSession, renameSession, useSessionPrefs } from '../services/sessionPrefs'
import { listSessions } from '../services/shopping'
import type { SessionSummary } from '../types/shopping'

export default function History() {
  const [items, setItems] = useState<SessionSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [sort, setSort] = useState<SortKey>('recent')
  const [pendingDelete, setPendingDelete] = useState<SessionSummary | null>(null)
  const prefs = useSessionPrefs()

  const load = useCallback(() => {
    setError(null)
    setItems(null)
    listSessions()
      .then(setItems)
      .catch((e) => setError(errorMessage(e)))
  }, [])
  useEffect(load, [load])

  const titleOf = useCallback((s: SessionSummary) => prefs.titles[s.id] ?? s.query, [prefs.titles])
  const all = useMemo(() => (items ?? []).filter((s) => !prefs.hidden.includes(s.id)), [items, prefs.hidden])
  const statusOptions = useMemo(() => [...new Set(all.map((s) => statusInfo(s.status).text))], [all])

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    const list = all.filter(
      (s) =>
        (status === 'all' || statusInfo(s.status).text === status) &&
        (!q || titleOf(s).toLowerCase().includes(q) || (s.product_name ?? '').toLowerCase().includes(q)),
    )
    const at = (s: SessionSummary) => s.created_at ?? ''
    if (sort === 'oldest') return list.sort((a, b) => at(a).localeCompare(at(b)))
    if (sort === 'alpha') return list.sort((a, b) => titleOf(a).localeCompare(titleOf(b)))
    return list.sort((a, b) => at(b).localeCompare(at(a)))
  }, [all, search, status, sort, titleOf])

  const filtersActive = search.trim() !== '' || status !== 'all' || sort !== 'recent'
  const clear = () => {
    setSearch('')
    setStatus('all')
    setSort('recent')
  }
  // Date headings only make sense when the list is newest-first.
  const groups = sort === 'recent' ? groupByDate(visible) : [{ label: sort === 'oldest' ? 'Oldest first' : 'A to Z', items: visible }]

  return (
    <Shell title="Shopping History">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-8 md:px-6">
        <div className="mx-auto w-full max-w-[860px]">
          <header>
            <h1 className="text-[24px] font-semibold leading-8 tracking-tight text-fg">Shopping History</h1>
            <p className="mt-1 text-[14px] text-fg-2">Review your previous searches and shopping sessions.</p>
          </header>

          <div className="mt-6">
            <HistoryToolbar
              search={search}
              onSearch={setSearch}
              status={status}
              statusOptions={statusOptions}
              onStatus={setStatus}
              sort={sort}
              onSort={setSort}
              filtersActive={filtersActive}
              onClear={clear}
            />
          </div>

          <div className="mt-8">
            {error ? (
              <div className="rounded-card border border-line bg-white p-6 text-center">
                <p className="text-[14px] text-fg">We couldn&apos;t load your shopping history.</p>
                <p className="mt-1 text-[13px] text-fg-3">{error}</p>
                <button className="btn-ghost mt-4" onClick={load}>
                  Retry
                </button>
              </div>
            ) : items === null ? (
              <HistorySkeleton />
            ) : all.length === 0 ? (
              <EmptyHistoryState />
            ) : visible.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-[14px] text-fg">No sessions match your filters.</p>
                <button className="btn-ghost mt-4" onClick={clear}>
                  Clear filters
                </button>
              </div>
            ) : (
              <div className="space-y-8">
                {groups.map((g) => (
                  <section key={g.label}>
                    <h2 className="mb-3 text-[12px] font-semibold uppercase tracking-wider text-fg-3">{g.label}</h2>
                    <div className="space-y-3">
                      {g.items.map((s) => (
                        <HistoryCard
                          key={s.id}
                          session={s}
                          title={titleOf(s)}
                          onRename={(t) => renameSession(s.id, t)}
                          onDelete={() => setPendingDelete(s)}
                        />
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        title="Delete this conversation?"
        description={`"${pendingDelete ? titleOf(pendingDelete) : ''}" will be removed from your history.`}
        confirmLabel="Delete"
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) hideSession(pendingDelete.id)
          setPendingDelete(null)
        }}
      />
    </Shell>
  )
}
