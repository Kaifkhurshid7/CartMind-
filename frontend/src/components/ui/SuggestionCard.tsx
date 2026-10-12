import type { ReactNode } from 'react'

/** Full-width suggestion row; clicking hands the prompt back to the caller. */
export default function SuggestionCard({ text, icon, onPick }: { text: string; icon: ReactNode; onPick: (text: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onPick(text)}
      className="flex min-h-[52px] w-full items-center gap-3 rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left text-[14px] leading-5 text-zinc-700 transition hover:border-zinc-300 hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/30"
    >
      <span className="shrink-0 text-zinc-400">{icon}</span>
      <span className="min-w-0 flex-1">{text}</span>
    </button>
  )
}
