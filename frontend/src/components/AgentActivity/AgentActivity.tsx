import { useEffect, useState } from 'react'
import type { AgentEvent } from '../../types/agent'
import type { SessionStatus } from '../../types/shopping'
import { CheckIcon, ChevronDown, HourglassIcon, XIcon } from '../icons'

const GLYPH: Record<string, { g: JSX.Element; cls: string }> = {
  done: { g: <CheckIcon width={14} height={14} />, cls: 'text-emerald-600' },
  error: { g: <XIcon width={14} height={14} />, cls: 'text-rose-600' },
  waiting: { g: <HourglassIcon width={14} height={14} />, cls: 'text-amber-600' },
  running: { g: <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-600" />, cls: 'text-blue-600' },
}

const BUSY = new Set(['started', 'running', 'executing', 'waiting_for_user'])

/** Collapsible step list: open while the agent works, tucked away once it is idle. */
export default function AgentActivity({ events, status }: { events: AgentEvent[]; status?: SessionStatus }) {
  const busy = !!status && BUSY.has(status)
  const [open, setOpen] = useState(true)
  useEffect(() => setOpen(busy), [busy])

  if (events.length === 0) return null
  const last = events[events.length - 1]

  return (
    <section className="rounded-xl border border-zinc-200 bg-zinc-50/60" aria-label="Agent activity">
      <button className="flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="font-medium text-zinc-800">
          Agent activity <span className="font-normal text-zinc-400">· {events.length} steps</span>
        </span>
        <span className="flex min-w-0 items-center gap-2 text-xs text-zinc-500">
          {!open && <span className="truncate">{last.message}</span>}
          <ChevronDown className={`shrink-0 transition ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>
      {open && (
        <ol className="max-h-64 space-y-1.5 overflow-y-auto border-t border-zinc-200 px-4 py-3 text-[13px]">
          {events.map((e, i) => {
            const resolved = e.status === 'waiting' && i < events.length - 1
            const icon = GLYPH[resolved ? 'done' : e.status] ?? GLYPH.done
            return (
              <li key={e.id} className="flex gap-2.5">
                <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center ${icon.cls}`}>{icon.g}</span>
                <span className={e.status === 'error' ? 'text-rose-700' : 'text-zinc-600'}>{e.message}</span>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
