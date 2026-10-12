import { KeyboardEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import type { SessionSummary } from '../../types/shopping'
import { timeAgo } from '../../services/time'
import { PencilIcon, TrashIcon } from '../icons'
import { StatusDot } from '../ui/StatusBadge'

interface Props {
  session: SessionSummary
  title: string
  active: boolean
  onNavigate: () => void
  onRename: (title: string) => void
  onDelete: () => void
}

/** One conversation row: truncated title, status dot, hover rename/delete. */
export default function HistoryItem({ session, title, active, onNavigate, onRename, onDelete }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)

  function commit() {
    setEditing(false)
    if (draft.trim() !== title) onRename(draft)
  }
  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') commit()
    if (e.key === 'Escape') setEditing(false)
  }

  if (editing) {
    return (
      <input
        autoFocus
        value={draft}
        aria-label="Conversation title"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={onKey}
        className="h-9 w-full rounded-lg border border-zinc-300 bg-white px-3 text-[14px] text-zinc-900 outline-none focus:ring-2 focus:ring-zinc-900/20"
      />
    )
  }

  return (
    <div
      className={`group relative flex h-9 items-center rounded-lg transition ${
        active ? 'bg-zinc-200/70 text-zinc-900' : 'text-zinc-700 hover:bg-zinc-200/40'
      }`}
    >
      <Link
        to={`/session/${session.id}`}
        onClick={onNavigate}
        title={`${title} · ${timeAgo(session.created_at)}`}
        aria-current={active ? 'page' : undefined}
        className={`flex h-full min-w-0 flex-1 items-center gap-2 rounded-lg px-3 text-[14px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/30 ${
          active ? 'font-medium' : ''
        }`}
      >
        <span className="min-w-0 flex-1 truncate">{title}</span>
        <span className="group-hover:hidden group-focus-within:hidden">
          <StatusDot status={session.status} />
        </span>
      </Link>
      <span className="absolute right-1 hidden items-center gap-0.5 group-focus-within:flex group-hover:flex">
        <button
          className="icon-btn bg-inherit"
          aria-label={`Rename ${title}`}
          title="Rename"
          onClick={() => {
            setDraft(title)
            setEditing(true)
          }}
        >
          <PencilIcon width={14} height={14} />
        </button>
        <button
          className="icon-btn bg-inherit hover:!text-rose-600"
          aria-label={`Delete ${title}`}
          title="Delete"
          onClick={() => {
            if (window.confirm('Delete this conversation from your history?')) onDelete()
          }}
        >
          <TrashIcon width={14} height={14} />
        </button>
      </span>
    </div>
  )
}
