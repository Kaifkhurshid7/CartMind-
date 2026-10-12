import { KeyboardEvent, useMemo, useState } from 'react'
import { SearchIcon, SparkIcon } from '../icons'

export const STARTER_PROMPTS = [
  'Find a laptop under ₹50,000 for coding with 16GB RAM and 512GB SSD',
  'Wireless headphones under ₹3,000 with ANC and good battery life',
  'Best smartphone under ₹25,000 with a great camera and 8GB RAM',
  'Paperback of "Atomic Habits" by James Clear under ₹500 with a good rating',
  'A 1.5 litre electric kettle under ₹1,500 rated 4 stars or more',
]

export const FOLLOW_UP_PROMPTS = [
  'Why did you choose this one?',
  'Show me a cheaper alternative',
  'Which option has the best reviews?',
  'Increase my budget by 20% and search again',
  'Prioritise battery life over price',
]

/** Light suggestion picker: searchable list of ready-made shopping requests. */
export default function PromptLibrary({
  prompts,
  onPick,
  title = 'Shopping ideas',
  maxListHeight = 256,
}: {
  prompts: string[]
  onPick: (prompt: string) => void
  title?: string
  /** Pixels available for the list so the popup never leaves the viewport. */
  maxListHeight?: number
}) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const shown = useMemo(() => prompts.filter((p) => p.toLowerCase().includes(query.trim().toLowerCase())), [prompts, query])

  function onKey(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => Math.min(i + 1, shown.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && shown[active]) {
      e.preventDefault()
      onPick(shown[active])
    }
  }

  return (
    <div className="w-[min(92vw,460px)] animate-fade-in overflow-hidden rounded-card border border-line bg-white shadow-lg">
      <div className="border-b border-line p-2">
        <label className="flex h-9 items-center gap-2 rounded-control px-2 text-fg-3 focus-within:bg-hover">
          <SearchIcon width={15} height={15} className="shrink-0" />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActive(0)
            }}
            onKeyDown={onKey}
            placeholder="Search ideas"
            aria-label="Search shopping ideas"
            className="min-w-0 flex-1 bg-transparent text-[14px] text-fg outline-none placeholder:text-placeholder"
          />
        </label>
      </div>

      <p className="px-4 pb-1 pt-3 text-[12px] font-medium text-fg-3">{title}</p>
      <ul className="thread-scroll overflow-y-auto overscroll-contain px-2 pb-2" style={{ maxHeight: maxListHeight }} role="listbox" aria-label={title}>
        {shown.length === 0 && <li className="px-3 py-3 text-[13px] text-fg-3">No matching ideas</li>}
        {shown.map((p, i) => (
          <li key={p}>
            <button
              type="button"
              role="option"
              aria-selected={i === active}
              onMouseEnter={() => setActive(i)}
              onClick={() => onPick(p)}
              className={`flex w-full items-start gap-3 rounded-control px-3 py-2.5 text-left text-[14px] leading-5 transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
                i === active ? 'bg-hover text-fg' : 'text-fg-2'
              }`}
            >
              <SparkIcon width={15} height={15} className="mt-0.5 shrink-0 text-fg-3" />
              <span className="min-w-0 flex-1">{p}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
