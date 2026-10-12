import type { ReactNode } from 'react'

interface Props {
  icon: ReactNode
  title: string
  meta: string
  /** Full request handed to the composer when the card is chosen. */
  prompt: string
  onPick: (prompt: string) => void
}

/** Starter card: icon tile, short title and the key constraints. The whole card is the button. */
export default function SuggestionCard({ icon, title, meta, prompt, onPick }: Props) {
  return (
    <button
      type="button"
      onClick={() => onPick(prompt)}
      title={prompt}
      className="flex h-full w-full flex-row items-center gap-3 rounded-card border border-line bg-white p-4 text-left transition duration-fast hover:-translate-y-px hover:border-line-strong hover:bg-hover active:translate-y-0 active:bg-hover-nav focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 sm:flex-col sm:items-start sm:gap-4"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-hover text-fg-2">{icon}</span>
      <span className="min-w-0">
        <span className="block text-[14px] font-medium leading-5 text-fg">{title}</span>
        <span className="mt-0.5 block text-[13px] leading-5 text-fg-3">{meta}</span>
      </span>
    </button>
  )
}
