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
        className="h-9 w-full rounded-control border border-line-strong bg-white px-3 text-[14px] text-fg outline-none focus:ring-2 focus:ring-primary/10"
      />
    )
  }

  return (
    <div
      className={`group flex min-h-10 items-center rounded-control transition-colors duration-fast ${
        active ? 'bg-active-nav text-fg' : 'text-fg-2 hover:bg-hover-nav hover:text-fg'
      }`}
    >
      <Link
        to={`/session/${session.id}`}
        onClick={onNavigate}
        title={`${title} · ${timeAgo(session.created_at)}`}
        aria-current={active ? 'page' : undefined}
        className={`flex min-h-10 min-w-0 flex-1 items-center gap-2 rounded-control px-3 py-1.5 text-[13.5px] leading-[18px] focus-ring ${active ? 'font-medium' : ''}`}
      >
        <span className="line-clamp-2 min-w-0 flex-1 break-words">{title}</span>
        <span className="group-focus-within:hidden group-hover:hidden">
          <StatusDot status={session.status} />
        </span>
      </Link>
      <span className="mr-1 hidden shrink-0 items-center gap-0.5 group-focus-within:flex group-hover:flex">
        <button
          className="icon-btn"
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
          className="icon-btn hover:!text-rose-600"
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
