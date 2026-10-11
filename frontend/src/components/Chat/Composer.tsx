import { FormEvent, KeyboardEvent, useEffect, useRef } from 'react'
import type { Health } from '../../hooks/useHealth'
import { PlusCircle, SendIcon, SparkIcon, StoreIcon } from '../icons'

interface Props {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  onPlus?: () => void
  health: Health | null
  placeholder?: string
  disabled?: boolean
  sending?: boolean
  autoFocus?: boolean
}

/** The rounded message box: source pill on top, white input with model chip + Send below. */
export default function Composer({ value, onChange, onSubmit, onPlus, health, placeholder, disabled, sending, autoFocus }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [value])

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (!disabled && !sending && value.trim()) onSubmit()
  }
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault() // otherwise a newline lands in the just-cleared box
      submit()
    }
  }

  const model = health ? (health.llm_model ?? 'Rule-based mode') : '…'

  return (
    <form onSubmit={submit} className="rounded-2xl border border-zinc-200/70 bg-zinc-100/80 p-2 shadow-sm">
      <div className="flex items-center justify-between px-1.5 pb-2 pt-0.5">
        <button type="button" className="text-zinc-400 hover:text-zinc-700" aria-label="Start a new search" title="New search" onClick={onPlus}>
          <PlusCircle />
        </button>
        <span
          className="inline-flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-1 text-xs font-medium text-zinc-700 shadow-[0_0_0_1px_rgba(0,0,0,0.06)]"
          title={health?.shopping_mode === 'live' ? 'Shopping on the live site' : 'Offline demo store'}
        >
          <StoreIcon width={14} height={14} />
          {health?.site ?? 'Store'}
        </span>
      </div>

      <div className="rounded-xl bg-white px-4 pb-2.5 pt-3 shadow-[0_1px_2px_rgba(0,0,0,0.06)]">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          autoFocus={autoFocus}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKey}
          placeholder={placeholder}
          aria-label="Message"
          className="block w-full resize-none bg-transparent text-[15px] leading-6 text-zinc-900 outline-none placeholder:text-zinc-400 disabled:cursor-not-allowed"
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs text-zinc-700">
            <SparkIcon width={13} height={13} className="text-amber-600" />
            {model}
          </span>
          <button
            type="submit"
            disabled={disabled || sending || !value.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-zinc-900 px-3.5 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <SendIcon width={15} height={15} />
            Send
            <kbd className="rounded bg-white/20 px-1.5 text-[11px] leading-5">↵</kbd>
          </button>
        </div>
      </div>
    </form>
  )
}
