export function timeAgo(iso: string | undefined | null, now = Date.now()): string {
  if (!iso) return ''
  const diff = Math.max(0, now - new Date(iso).getTime())
  const min = Math.floor(diff / 60_000)
  if (min < 1) return 'just now'
  if (min < 60) return `${min} min ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} hr ago`
  return new Date(iso).toLocaleDateString()
}

export function dayLabel(iso: string | undefined | null): string {
  if (!iso) return 'TODAY'
  const d = new Date(iso)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return 'TODAY'
  const y = new Date(today)
  y.setDate(today.getDate() - 1)
  if (d.toDateString() === y.toDateString()) return 'YESTERDAY'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }).toUpperCase()
}
