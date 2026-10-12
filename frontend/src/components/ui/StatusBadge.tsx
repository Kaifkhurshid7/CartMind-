import type { SessionStatus } from '../../types/shopping'

export const STATUS_LABEL: Record<SessionStatus, { text: string; cls: string; dot: string }> = {
  started: { text: 'Starting', cls: 'bg-blue-50 text-blue-700', dot: 'bg-blue-500' },
  running: { text: 'Working', cls: 'bg-blue-50 text-blue-700', dot: 'bg-blue-500' },
  waiting_for_approval: { text: 'Needs approval', cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' },
  executing: { text: 'Shopping', cls: 'bg-blue-50 text-blue-700', dot: 'bg-blue-500' },
  waiting_for_user: { text: 'Needs you', cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' },
  price_changed: { text: 'Price changed', cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' },
  completed: { text: 'In cart', cls: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500' },
  cancelled: { text: 'Cancelled', cls: 'bg-zinc-100 text-zinc-600', dot: 'bg-zinc-300' },
  failed: { text: 'Failed', cls: 'bg-rose-50 text-rose-700', dot: 'bg-rose-500' },
  no_results: { text: 'No match', cls: 'bg-rose-50 text-rose-700', dot: 'bg-rose-400' },
  needs_clarification: { text: 'Needs info', cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-400' },
}

const FALLBACK = { cls: 'bg-zinc-100 text-zinc-600', dot: 'bg-zinc-300' }

export function statusInfo(status: string) {
  return STATUS_LABEL[status as SessionStatus] ?? { text: status, ...FALLBACK }
}

export function StatusDot({ status }: { status: string }) {
  const s = statusInfo(status)
  return <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${s.dot}`} aria-hidden="true" />
}

export default function StatusBadge({ status }: { status: string }) {
  const s = statusInfo(status)
  return <span className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-medium ${s.cls}`}>{s.text}</span>
}
