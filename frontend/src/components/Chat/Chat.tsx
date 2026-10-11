import { ReactNode, useState } from 'react'
import { timeAgo } from '../../services/time'
import { CheckIcon, CopyIcon, ThumbDown, ThumbUp } from '../icons'

export function DayDivider({ label }: { label: string }) {
  return (
    <div className="my-6 flex items-center gap-4 text-[11px] font-medium tracking-wider text-zinc-400">
      <span className="h-px flex-1 bg-zinc-200" />
      {label}
      <span className="h-px flex-1 bg-zinc-200" />
    </div>
  )
}

function Byline({ name, at }: { name: string; at?: string }) {
  return (
    <p className="mb-1.5 text-sm">
      <span className="font-semibold text-zinc-900">{name}</span>
      {at && <span className="text-zinc-400"> • {timeAgo(at)}</span>}
    </p>
  )
}

/** Right-aligned grey bubble, as in the reference design. */
export function UserMessage({ text, at }: { text: string; at?: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[78%] rounded-2xl bg-zinc-100 px-4 py-3">
        <Byline name="Me" at={at} />
        <p className="whitespace-pre-wrap text-[15px] leading-6 text-zinc-800">{text}</p>
      </div>
    </div>
  )
}

type Vote = 'up' | 'down' | null

/** Plain left-aligned agent message with copy / thumbs actions underneath. */
export function AgentMessage({
  id,
  text,
  at,
  children,
}: {
  id: string
  text: string
  at?: string
  children?: ReactNode
}) {
  const key = `cartmind:vote:${id}`
  const [vote, setVote] = useState<Vote>(() => {
    try {
      return (localStorage.getItem(key) as Vote) || null
    } catch {
      return null
    }
  })
  const [copied, setCopied] = useState(false)

  function choose(v: Exclude<Vote, null>) {
    const next = vote === v ? null : v
    setVote(next)
    try {
      next ? localStorage.setItem(key, next) : localStorage.removeItem(key)
    } catch {
      /* storage unavailable */
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div className="max-w-[92%]">
      <Byline name="CartMind" at={at} />
      <p className="whitespace-pre-wrap text-[15px] leading-6 text-zinc-800">{text}</p>
      {children && <div className="mt-3 space-y-3">{children}</div>}
      <div className="mt-2 flex items-center gap-0.5">
        <button className={`icon-btn ${vote === 'up' ? '!text-zinc-900' : ''}`} aria-label="Good response" aria-pressed={vote === 'up'} onClick={() => choose('up')}>
          <ThumbUp />
        </button>
        <button className={`icon-btn ${vote === 'down' ? '!text-zinc-900' : ''}`} aria-label="Bad response" aria-pressed={vote === 'down'} onClick={() => choose('down')}>
          <ThumbDown />
        </button>
        <button className="icon-btn" aria-label="Copy response" onClick={copy}>
          {copied ? <CheckIcon /> : <CopyIcon />}
        </button>
      </div>
    </div>
  )
}

export function TypingIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-zinc-500" aria-live="polite">
      <span className="flex gap-1">
        <i className="dot h-1.5 w-1.5 rounded-full bg-zinc-400" />
        <i className="dot h-1.5 w-1.5 rounded-full bg-zinc-400" />
        <i className="dot h-1.5 w-1.5 rounded-full bg-zinc-400" />
      </span>
      {label}
    </div>
  )
}
