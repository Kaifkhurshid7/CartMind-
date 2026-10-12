import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../../services/api'
import { improvePrompt } from '../../services/shopping'
import { ArrowUp, BagIcon, SparkIcon } from '../icons'
import Popover from '../ui/Popover'
import PromptLibrary from './PromptLibrary'

interface Props {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  prompts: string[]
  placeholder?: string
  disabled?: boolean
  sending?: boolean
  autoFocus?: boolean
}

/** Rounded message box with a prompt library, prompt improver and a round send button. */
export default function Composer({ value, onChange, onSubmit, prompts, placeholder, disabled, sending, autoFocus }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const [library, setLibrary] = useState(false)
  const [improving, setImproving] = useState(false)
  const [note, setNote] = useState<string | null>(null)
  const closeLibrary = useCallback(() => setLibrary(false), [])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`
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

  async function improve() {
    if (!value.trim() || improving) return
    setImproving(true)
    setNote(null)
    try {
      onChange(await improvePrompt(value.trim()))
    } catch (e) {
      setNote(errorMessage(e))
    } finally {
      setImproving(false)
    }
  }

  return (
    <form onSubmit={submit} className="relative rounded-2xl border border-zinc-200 bg-white p-4 shadow-[0_2px_12px_rgba(0,0,0,0.05)]">
      <Popover open={library} onClose={closeLibrary} className="bottom-full left-6 mb-2">
        <PromptLibrary
          prompts={prompts}
          onPick={(p) => {
            onChange(p)
            setLibrary(false)
            ref.current?.focus()
          }}
        />
      </Popover>

      <textarea
        ref={ref}
        rows={1}
        value={value}
        autoFocus={autoFocus}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKey}
        placeholder={placeholder ?? 'Ask me anything'}
        aria-label="Message"
        className="block min-h-[28px] w-full resize-none bg-transparent text-[15px] leading-7 text-zinc-900 outline-none placeholder:text-zinc-400 disabled:cursor-not-allowed"
      />

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setLibrary((o) => !o)}
            aria-haspopup="dialog"
            aria-expanded={library}
            className={`inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-[13px] font-medium transition ${
              library ? 'border-zinc-300 bg-zinc-100 text-zinc-900' : 'border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-50'
            }`}
          >
            <BagIcon width={15} height={15} />
            Prompt Library
          </button>
          <button
            type="button"
            onClick={improve}
            disabled={!value.trim() || improving || disabled}
            className="inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-[13px] font-medium text-zinc-600 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <SparkIcon width={15} height={15} className={improving ? 'animate-pulse' : ''} />
            {improving ? 'Improving…' : 'Improve Prompt'}
          </button>
        </div>
        <button
          type="submit"
          aria-label="Send message"
          disabled={disabled || sending || !value.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ArrowUp width={18} height={18} />
        </button>
      </div>
      {note && <p className="mt-2 text-xs text-rose-600">{note}</p>}
    </form>
  )
}
