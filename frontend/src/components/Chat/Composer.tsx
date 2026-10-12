import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../../services/api'
import { improvePrompt } from '../../services/shopping'
import { ArrowUp, ListIcon, SparkIcon } from '../icons'
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
  const [listMax, setListMax] = useState(256)
  const formRef = useRef<HTMLFormElement>(null)
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

  // Fit the ideas list into the space above the composer (below the 48px top bar).
  function toggleLibrary() {
    const top = formRef.current?.getBoundingClientRect().top ?? 400
    setListMax(Math.max(120, Math.min(256, top - 48 - 16 - 108)))
    setLibrary((o) => !o)
  }

  async function improve() {
    if (improving) return
    if (!value.trim()) {
      setNote('Write what you want to buy first, then I can improve it.')
      return
    }
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
    <form ref={formRef} onSubmit={submit} className="relative rounded-card border border-line bg-white p-3 shadow-composer transition-colors duration-fast focus-within:border-line-strong focus-within:ring-2 focus-within:ring-primary/5">
      <Popover open={library} onClose={closeLibrary} className="bottom-full left-0 mb-2">
        <PromptLibrary
          prompts={prompts}
          maxListHeight={listMax}
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
        placeholder={placeholder ?? "Tell CartMind what you're looking to buy..."}
        aria-label="Message"
        className="block min-h-[28px] w-full resize-none bg-transparent px-1 text-[15px] leading-7 text-fg outline-none placeholder:text-placeholder disabled:cursor-not-allowed"
      />

      <div className="mt-2 flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={toggleLibrary}
            aria-haspopup="dialog"
            aria-expanded={library}
            className={`inline-flex items-center gap-2 rounded-control border px-3 py-1.5 text-[13px] font-medium transition-colors duration-fast focus-ring ${
              library ? 'border-line-strong bg-hover text-fg' : 'border-line bg-white text-fg-2 hover:bg-hover hover:text-fg'
            }`}
          >
            <ListIcon width={15} height={15} />
            Shopping ideas
          </button>
          <button
            type="button"
            onClick={improve}
            disabled={improving || disabled}
            className="inline-flex items-center gap-2 rounded-control px-3 py-1.5 text-[13px] font-medium text-fg-2 transition-colors duration-fast hover:bg-hover hover:text-fg focus-ring disabled:cursor-not-allowed disabled:text-disabled-fg"
          >
            <SparkIcon width={15} height={15} className={improving ? 'animate-pulse' : ''} />
            {improving ? 'Improving…' : 'Improve Prompt'}
          </button>
        </div>
        <button
          type="submit"
          aria-label="Send message"
          disabled={disabled || sending || !value.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-white transition-colors duration-fast hover:bg-primary-hover active:bg-primary-active focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-disabled-bg disabled:text-disabled-fg"
        >
          <ArrowUp width={18} height={18} />
        </button>
      </div>
      {note && <p className="mt-2 px-1 text-xs text-fg-3" role="status">{note}</p>}
    </form>
  )
}
