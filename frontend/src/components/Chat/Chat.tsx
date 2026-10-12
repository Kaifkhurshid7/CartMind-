import { ReactNode, useState } from 'react'
import { stripEmoji } from '../../services/text'
import { timeAgo } from '../../services/time'
import { CheckIcon, ChevronDown, CopyIcon, FilledThumb, HourglassIcon, LogoMark, ThumbDown, ThumbUp } from '../icons'

export function DayDivider({ label }: { label: string }) {
  return (
    <div className="my-6 flex items-center gap-4 text-[11px] font-medium tracking-wider text-zinc-400">
      <span className="h-px flex-1 bg-zinc-200/80" />
      {label}
      <span className="h-px flex-1 bg-zinc-200/80" />
    </div>
  )
}

/** Right-aligned rounded pill for the shopper's messages. */
export function UserMessage({ text, at }: { text: string; at?: string }) {
  return (
    <div className="flex justify-end">
      <p
        title={at ? timeAgo(at) : undefined}
        className="max-w-[80%] whitespace-pre-wrap rounded-3xl bg-zinc-100 px-5 py-3 text-[15px] leading-6 text-zinc-800"
      >
        {text}
      </p>
    </div>
  )
}

type Vote = 'up' | 'down' | null

/** Bordered assistant card: logo, collapse chevron, message, rich content, follow-up chips. */
export function AgentMessage({
  id,
  text,
  at,
  children,
  chips,
  onChip,
}: {
  id: string
  text: string
  at?: string
  children?: ReactNode
  chips?: string[]
  onChip?: (chip: string) => void
}) {
  const key = `cartmind:vote:${id}`
  const clean = stripEmoji(text)
  const [open, setOpen] = useState(true)
  const [copied, setCopied] = useState(false)
  const [vote, setVote] = useState<Vote>(() => {
    try {
      return (localStorage.getItem(key) as Vote) || null
    } catch {
      return null
    }
  })

  function choose(v: Exclude<Vote, null>) {
    const next = vote === v ? null : v
    setVote(next)
    try {
      if (next) localStorage.setItem(key, next)
      else localStorage.removeItem(key)
    } catch {
      /* storage unavailable */
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(clean)
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <article className="group rounded-2xl border border-zinc-200 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
      <div className="flex items-center justify-between">
        <LogoMark size={24} />
        <div className="flex items-center gap-1">
          <span className="mr-1 hidden text-xs text-zinc-400 group-hover:inline">{at ? timeAgo(at) : ''}</span>
          <button className="icon-btn" aria-label={open ? 'Collapse message' : 'Expand message'} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            <ChevronDown className={`transition ${open ? '' : '-rotate-90'}`} />
          </button>
        </div>
      </div>

      {open ? (
        <>
          <p className="mt-3 whitespace-pre-wrap text-[15px] leading-7 text-zinc-800">{clean}</p>
          {children && <div className="mt-4 space-y-4">{children}</div>}
          {chips && chips.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {chips.map((c) => (
                <button
                  key={c}
                  onClick={() => onChip?.(c)}
                  className="rounded-xl bg-zinc-100 px-3 py-1.5 text-[13px] text-zinc-700 transition hover:bg-zinc-200"
                >
                  {c}
                </button>
              ))}
            </div>
          )}
          <div className="mt-3 flex items-center gap-1 text-zinc-500">
            <button
              className={`icon-btn !h-8 !w-8 ${vote === 'up' ? '!bg-emerald-50 !text-emerald-700' : ''}`}
              aria-label="Good response"
              title="Good response"
              aria-pressed={vote === 'up'}
              onClick={() => choose('up')}
            >
              {vote === 'up' ? <FilledThumb /> : <ThumbUp />}
            </button>
            <button
              className={`icon-btn !h-8 !w-8 ${vote === 'down' ? '!bg-rose-50 !text-rose-700' : ''}`}
              aria-label="Bad response"
              title="Bad response"
              aria-pressed={vote === 'down'}
              onClick={() => choose('down')}
            >
              {vote === 'down' ? <FilledThumb down /> : <ThumbDown />}
            </button>
            {vote && <span className="ml-1 text-xs text-zinc-500" aria-live="polite">Thanks for the feedback</span>}
            <button className="icon-btn !h-8 !w-8" aria-label="Copy response" title="Copy response" onClick={copy}>
              {copied ? <CheckIcon /> : <CopyIcon />}
            </button>
          </div>
        </>
      ) : (
        <p className="mt-2 truncate text-sm text-zinc-400">{clean}</p>
      )}
    </article>
  )
}

export function Thinking({ detail }: { detail?: string }) {
  return (
    <div className="flex items-center gap-2.5 px-1 text-sm text-zinc-500" aria-live="polite">
      <HourglassIcon width={15} height={15} className="animate-pulse" />
      <span className="font-medium">Thinking…</span>
      {detail && <span className="truncate text-zinc-400">{detail}</span>}
    </div>
  )
}
