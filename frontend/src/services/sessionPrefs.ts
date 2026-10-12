/**
 * Client-side session preferences. The backend has no rename/delete endpoints yet,
 * so custom titles and hidden sessions live in localStorage behind this one module.
 */
import { useEffect, useState } from 'react'
import type { SessionSummary } from '../types/shopping'

const KEY = 'cartmind:session-prefs'
const EVENT = 'cartmind:session-prefs-changed'

interface Prefs {
  titles: Record<string, string>
  hidden: string[]
}

function read(): Prefs {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? '{}')
    return { titles: raw.titles ?? {}, hidden: raw.hidden ?? [] }
  } catch {
    return { titles: {}, hidden: [] }
  }
}

function write(p: Prefs) {
  try {
    localStorage.setItem(KEY, JSON.stringify(p))
  } catch {
    /* storage unavailable: change applies for this render only */
  }
  window.dispatchEvent(new Event(EVENT))
}

export function renameSession(id: string, title: string) {
  const p = read()
  const t = title.trim()
  if (t) p.titles[id] = t
  else delete p.titles[id]
  write(p)
}

export function hideSession(id: string) {
  const p = read()
  if (!p.hidden.includes(id)) p.hidden.push(id)
  write(p)
}

/** Re-renders when titles or hidden sessions change, in this tab or another. */
export function useSessionPrefs(): Prefs {
  const [prefs, setPrefs] = useState(read)
  useEffect(() => {
    const sync = () => setPrefs(read())
    window.addEventListener(EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])
  return prefs
}

export interface HistoryGroup {
  label: string
  items: SessionSummary[]
}

const DAY = 86_400_000

/** Newest first, bucketed into Today / Yesterday / Previous 7 Days / Older. */
export function groupByDate(items: SessionSummary[], now = new Date()): HistoryGroup[] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const buckets: HistoryGroup[] = [
    { label: 'Today', items: [] },
    { label: 'Yesterday', items: [] },
    { label: 'Previous 7 Days', items: [] },
    { label: 'Older', items: [] },
  ]
  const sorted = [...items].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
  for (const s of sorted) {
    const t = s.created_at ? new Date(s.created_at).getTime() : startOfToday
    const i = t >= startOfToday ? 0 : t >= startOfToday - DAY ? 1 : t >= startOfToday - 7 * DAY ? 2 : 3
    buckets[i].items.push(s)
  }
  return buckets.filter((b) => b.items.length > 0)
}
