import { KeyboardEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { inr } from '../../services/shopping'
import { timeAgo } from '../../services/time'
import type { SessionSummary } from '../../types/shopping'
import StatusBadge from '../ui/StatusBadge'
import HistoryActionsMenu from './HistoryActionsMenu'

interface Props {
  session: SessionSummary
  title: string
  onRename: (title: string) => void
  onDelete: () => void
}

/** One shopping session. The whole card is a link; the menu and rename field sit above it. */
export default function HistoryCard({ session, title, onRename, onDelete }: Props) {
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)
  const href = `/session/${session.id}`

  function commit() {
    setEditing(false)
    if (draft.trim() !== title) onRename(draft)
  }
  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') commit()
    if (e.key === 'Escape') setEditing(false)
  }

  const details = session.product_name
    ? [session.product_name.slice(0, 70), session.price != null ? inr(session.price) : null]
    : ['No product selected']

  return (
    <article className="group relative flex items-start gap-3 rounded-card border border-line bg-white p-5 transition-colors duration-fast hover:border-line-strong hover:bg-zinc-50/60 focus-within:border-line-strong sm:gap-4">
      <div className="min-w-0 flex-1">
        {editing ? (
          <input
            autoFocus
            value={draft}
            aria-label="Conversation title"
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={onKey}
            className="relative z-10 h-9 w-full rounded-control border border-line-strong bg-white px-3 text-[15px] text-fg outline-none focus:ring-2 focus:ring-primary/10"
          />
        ) : (
          <h3 className="text-[15px] font-medium leading-6 text-fg">
            <Link
              to={href}
              className="break-words before:absolute before:inset-0 before:rounded-card focus-visible:outline-none focus-visible:before:ring-2 focus-visible:before:ring-primary/30"
            >
              {title}
            </Link>
          </h3>
        )}
        <p className="mt-1 break-words text-[13px] leading-5 text-fg-2">{details.filter(Boolean).join(' · ')}</p>
        {session.created_at && <p className="mt-0.5 text-[12px] text-fg-3">Started {timeAgo(session.created_at)}</p>}
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <StatusBadge status={session.status} />
        <HistoryActionsMenu
          title={title}
          onOpen={() => navigate(href)}
          onRename={() => {
            setDraft(title)
            setEditing(true)
          }}
          onDelete={onDelete}
        />
      </div>
    </article>
  )
}
