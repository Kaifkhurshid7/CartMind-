import { useEffect, useRef, useState } from 'react'
import type { AgentEvent } from '../../types/agent'
import type { SessionStatus } from '../../types/shopping'
import { ChevronDown } from '../icons'

const BUSY = new Set(['started', 'running', 'executing', 'waiting_for_user'])

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin text-primary" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

/** Plain status dot: neutral when done, amber when it hit a problem or is waiting. */
function Dot({ tone }: { tone: 'done' | 'warn' }) {
  return <span className={`h-2 w-2 rounded-full ${tone === 'warn' ? 'bg-amber-400' : 'bg-zinc-300'}`} aria-hidden="true" />
}

function StepIcon({ event, live, resolved }: { event: AgentEvent; live: boolean; resolved: boolean }) {
  if (live) return <Spinner />
  const warn = event.status === 'error' || (event.status === 'waiting' && !resolved)
  return <Dot tone={warn ? 'warn' : 'done'} />
}

/** Live timeline of real agent events: open while working, summarised once idle. */
export default function AgentActivity({ events, status }: { events: AgentEvent[]; status?: SessionStatus }) {
  const busy = !!status && BUSY.has(status)
  const [open, setOpen] = useState(true)
  const listRef = useRef<HTMLOListElement>(null)
  useEffect(() => setOpen(busy), [busy])

  // Keep the newest step in view while the agent is working.
  useEffect(() => {
    const el = listRef.current
    if (open && el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [events.length, open])

  if (events.length === 0) return null
  const last = events[events.length - 1]
  const failed = !busy && (status === 'failed' || status === 'no_results')

  return (
    <section className="overflow-hidden rounded-card border border-line bg-white shadow-soft" aria-label="Agent activity">
      <button
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left focus-ring"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="flex min-w-0 items-center gap-3">
          {busy ? (
            <Spinner />
          ) : (
            <span className="flex h-4 w-4 shrink-0 items-center justify-center">
              <Dot tone={failed ? 'warn' : 'done'} />
            </span>
          )}
          <span className="min-w-0">
            <span className="block text-[14px] font-medium text-fg">
              {busy ? 'CartMind is working' : failed ? 'Search finished without a match' : 'Research complete'}
            </span>
            <span className="block truncate text-[12px] text-fg-3">
              {!open || !busy ? `${events.length} steps` : last.message}
              {!open && ` · ${last.message}`}
            </span>
          </span>
        </span>
        <ChevronDown className={`shrink-0 text-fg-3 transition-transform duration-base ${open ? 'rotate-180' : ''}`} />
      </button>

      {busy && (
        <div className="relative h-0.5 overflow-hidden bg-hover" role="progressbar" aria-label="Agent working">
          <div className="indeterminate absolute inset-y-0 w-1/4 rounded-full bg-primary" />
        </div>
      )}

      {open && (
        <ol ref={listRef} className="max-h-72 animate-fade-in overflow-y-auto border-t border-line px-4 py-3">
          {events.map((e, i) => {
            const isLast = i === events.length - 1
            const live = busy && isLast && e.status !== 'error'
            const resolved = e.status === 'waiting' && !isLast
            return (
              <li key={e.id} className="relative flex animate-fade-up gap-3 pb-3 last:pb-0">
                {!isLast && <span className="absolute left-[7.5px] top-5 bottom-0 w-px bg-line" aria-hidden="true" />}
                <span className="relative mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center bg-white">
                  <StepIcon event={e} live={live} resolved={resolved} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className={`min-w-0 break-words text-[13px] leading-5 ${live ? 'font-medium text-fg' : 'text-fg-2'}`}>{e.message}</p>
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}
