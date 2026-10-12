import { useMemo, useState } from 'react'
import { CheckIcon, SearchIcon } from '../icons'

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

/** Dark translucent picker with search, as in the reference design. */
export default function PromptLibrary({
  prompts,
  onPick,
}: {
  prompts: string[]
  onPick: (prompt: string) => void
}) {
  const [query, setQuery] = useState('')
  const [hover, setHover] = useState(0)
  const shown = useMemo(
    () => prompts.filter((p) => p.toLowerCase().includes(query.trim().toLowerCase())),
    [prompts, query],
  )

  return (
    <div className="w-[min(92vw,430px)] overflow-hidden rounded-2xl bg-zinc-800/95 p-1.5 text-sm text-zinc-100 shadow-2xl backdrop-blur">
      <ul className="max-h-64 overflow-y-auto" role="listbox">
        {shown.length === 0 && <li className="px-3 py-2 text-zinc-400">No matching prompts</li>}
        {shown.map((p, i) => (
          <li key={p}>
            <button
              type="button"
              role="option"
              aria-selected={i === hover}
              onMouseEnter={() => setHover(i)}
              onClick={() => onPick(p)}
              className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                i === hover ? 'bg-zinc-600/70 text-white' : 'text-zinc-200'
              }`}
            >
              <span>{p}</span>
              {i === hover && <CheckIcon width={14} height={14} className="shrink-0 text-zinc-300" />}
            </button>
          </li>
        ))}
      </ul>
      <label className="mt-1 flex items-center gap-2 border-t border-white/10 px-3 py-2.5 text-zinc-400">
        <SearchIcon width={15} height={15} />
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setHover(0)
          }}
          placeholder="Search…"
          aria-label="Search prompts"
          className="w-full bg-transparent text-zinc-100 outline-none placeholder:text-zinc-500"
        />
      </label>
    </div>
  )
}
