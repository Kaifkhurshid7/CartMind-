const LABEL: Record<string, string> = {
  performance: 'Performance',
  battery: 'Battery life',
  display: 'Display',
  camera: 'Camera',
  features: 'Features',
  rating: 'Customer rating',
  confidence: 'Review volume',
  value: 'Value for money',
}

const HINT: Record<string, string> = {
  rating: 'Average rating, adjusted for how many people rated it',
  confidence: 'How much review evidence backs the rating',
  value: 'How far the price sits below your budget',
  performance: 'Processor, memory and storage',
  battery: 'Battery life compared with the other options',
  display: 'Panel type and refresh rate',
  camera: 'Camera hardware and ratings',
  features: 'Notable features listed for the product',
}

function tier(v: number) {
  if (v >= 75) return { word: 'Strong', bar: 'bg-primary', text: 'text-fg' }
  if (v >= 45) return { word: 'Fair', bar: 'bg-fg-3', text: 'text-fg-2' }
  return { word: 'Weak', bar: 'bg-amber-500', text: 'text-amber-700' }
}

/** Why the product scored as it did: overall match plus one row per criterion (0-100, from the backend). */
export default function ScoreBreakdown({ scores, overall }: { scores: Record<string, number>; overall?: number }) {
  const rows = Object.entries(scores)
    .filter(([k]) => LABEL[k])
    .sort((a, b) => b[1] - a[1])
  if (rows.length === 0) return null

  return (
    <section className="overflow-hidden rounded-card border border-line bg-surface" aria-label="Score breakdown">
      <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h3 className="text-[13px] font-semibold text-fg">How it scored</h3>
        {overall != null && (
          <span className="text-[13px] text-fg-3">
            Overall match <span className="ml-1 text-[15px] font-semibold tabular-nums text-fg">{Math.round(overall)}%</span>
          </span>
        )}
      </header>
      <ul className="divide-y divide-line">
        {rows.map(([key, value]) => {
          const t = tier(value)
          return (
            <li
              key={key}
              title={HINT[key]}
              className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1.5 px-4 py-2.5 sm:grid-cols-[150px_1fr_72px]"
            >
              <span className="text-[13px] text-fg-2">{LABEL[key]}</span>
              <span className={`text-right text-[12px] sm:order-3 ${t.text}`}>
                <span className="tabular-nums">{Math.round(value)}</span>
                <span className="ml-1.5 text-fg-3">{t.word}</span>
              </span>
              <div className="col-span-2 h-1.5 overflow-hidden rounded-full bg-hover sm:order-2 sm:col-span-1" role="presentation">
                <div
                  className={`h-full rounded-full transition-[width] duration-base ${t.bar}`}
                  style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
