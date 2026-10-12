import type { SessionStatus } from '../../types/shopping'

type Info = { text: string; cls: string; dot: string }

const SUCCESS = 'bg-green-50 text-green-700'
const ERROR = 'bg-rose-50 text-rose-700'
const PROGRESS = 'bg-amber-50 text-amber-700'
const NEUTRAL = 'bg-zinc-100 text-zinc-600'

/** Only statuses the backend really produces; "completed" means the item reached the cart, never a purchase. */
export const STATUS_LABEL: Record<SessionStatus, Info> = {
  started: { text: 'In progress', cls: PROGRESS, dot: 'bg-amber-500' },
  running: { text: 'In progress', cls: PROGRESS, dot: 'bg-amber-500' },
  executing: { text: 'In progress', cls: PROGRESS, dot: 'bg-amber-500' },
  waiting_for_approval: { text: 'Needs approval', cls: PROGRESS, dot: 'bg-amber-500' },
  waiting_for_user: { text: 'Needs you', cls: PROGRESS, dot: 'bg-amber-500' },
  price_changed: { text: 'Price changed', cls: PROGRESS, dot: 'bg-amber-500' },
  needs_clarification: { text: 'Needs info', cls: PROGRESS, dot: 'bg-amber-400' },
  completed: { text: 'In cart', cls: SUCCESS, dot: 'bg-green-600' },
  cancelled: { text: 'Cancelled', cls: NEUTRAL, dot: 'bg-zinc-300' },
  failed: { text: 'Failed', cls: ERROR, dot: 'bg-rose-500' },
  no_results: { text: 'No match', cls: ERROR, dot: 'bg-rose-400' },
}

export function statusInfo(status: string): Info {
  return STATUS_LABEL[status as SessionStatus] ?? { text: status, cls: NEUTRAL, dot: 'bg-zinc-300' }
}

export function StatusDot({ status }: { status: string }) {
  return <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${statusInfo(status).dot}`} aria-hidden="true" />
}

export default function StatusBadge({ status }: { status: string }) {
  const s = statusInfo(status)
  return <span className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${s.cls}`}>{s.text}</span>
}
