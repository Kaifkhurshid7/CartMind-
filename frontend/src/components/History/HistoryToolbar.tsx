import { SearchIcon, XIcon } from '../icons'

export type SortKey = 'recent' | 'oldest' | 'alpha'

interface Props {
  search: string
  onSearch: (v: string) => void
  status: string
  statusOptions: string[]
  onStatus: (v: string) => void
  sort: SortKey
  onSort: (v: SortKey) => void
  filtersActive: boolean
  onClear: () => void
}

const select =
  'h-10 rounded-control border border-line bg-white px-3 text-[14px] text-fg outline-none transition-colors duration-fast hover:border-line-strong focus:border-line-strong focus:ring-2 focus:ring-primary/10'

/** Search, status filter and sort controls on one wrapping row. */
export default function HistoryToolbar({ search, onSearch, status, statusOptions, onStatus, sort, onSort, filtersActive, onClear }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex h-10 min-w-[200px] flex-1 items-center gap-2 rounded-control border border-line bg-white px-3 text-fg-3 transition-colors duration-fast focus-within:border-line-strong focus-within:ring-2 focus-within:ring-primary/10">
        <SearchIcon width={16} height={16} className="shrink-0" />
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Search your shopping history..."
          aria-label="Search your shopping history"
          className="min-w-0 flex-1 bg-transparent text-[14px] text-fg outline-none placeholder:text-placeholder"
        />
      </label>
      <select className={select} value={status} onChange={(e) => onStatus(e.target.value)} aria-label="Filter by status">
        <option value="all">All statuses</option>
        {statusOptions.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <select className={select} value={sort} onChange={(e) => onSort(e.target.value as SortKey)} aria-label="Sort sessions">
        <option value="recent">Most recent</option>
        <option value="oldest">Oldest first</option>
        <option value="alpha">Alphabetical</option>
      </select>
      {filtersActive && (
        <button
          className="inline-flex h-10 items-center gap-1.5 rounded-control px-3 text-[14px] text-fg-2 transition-colors duration-fast hover:bg-hover hover:text-fg focus-ring"
          onClick={onClear}
        >
          <XIcon width={14} height={14} />
          Clear filters
        </button>
      )}
    </div>
  )
}
