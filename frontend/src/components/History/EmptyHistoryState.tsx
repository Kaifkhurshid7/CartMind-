import { Link } from 'react-router-dom'

export default function EmptyHistoryState() {
  return (
    <div className="flex flex-col items-center px-4 py-16 text-center">
      <h2 className="text-[18px] font-semibold text-fg">No shopping sessions yet</h2>
      <p className="mt-2 max-w-sm text-[14px] leading-6 text-fg-2">Your previous product searches and comparisons will appear here.</p>
      <Link to="/" className="btn-primary mt-6 h-10 px-5">
        Start Shopping
      </Link>
    </div>
  )
}

export function HistorySkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading history">
      {[0, 1, 2].map((i) => (
        <div key={i} className="animate-pulse rounded-card border border-line bg-white p-5">
          <div className="h-4 w-2/3 rounded bg-zinc-100" />
          <div className="mt-3 h-3 w-1/2 rounded bg-zinc-100" />
          <div className="mt-2 h-3 w-24 rounded bg-zinc-100" />
        </div>
      ))}
    </div>
  )
}
