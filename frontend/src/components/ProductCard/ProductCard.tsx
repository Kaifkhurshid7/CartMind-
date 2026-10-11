import { inr } from '../../services/shopping'
import type { Product } from '../../types/product'

const SPEC_LABEL: Record<string, (v: string | number | boolean) => string | null> = {
  ram_gb: (v) => `${v}GB RAM`,
  storage_gb: (v) => `${v}GB storage`,
  battery_hours: (v) => `${v}h battery`,
  battery_mah: (v) => `${v}mAh`,
  camera_mp: (v) => `${v}MP camera`,
  anc: (v) => (v ? 'ANC' : null),
  processor: (v) => String(v),
  type: (v) => String(v),
  display: (v) => String(v),
}

export function specChips(p: Product): string[] {
  return Object.entries(p.specs)
    .map(([k, v]) => SPEC_LABEL[k]?.(v) ?? null)
    .filter((x): x is string => !!x)
}

const SOURCE_LABEL: Record<string, string> = {
  amazon_in: 'Amazon.in',
  'amazon.in': 'Amazon.in',
  'flipkart.com': 'Flipkart',
  cartmart: 'Demo store',
}

interface Props {
  product: Product
  highlight?: boolean
  actionLabel?: string
  onAction?: () => void
  disabled?: boolean
}

export default function ProductCard({ product, highlight, actionLabel, onAction, disabled }: Props) {
  return (
    <article
      className={`flex flex-col gap-3 rounded-xl border bg-white p-4 ${highlight ? 'border-zinc-900 shadow-sm' : 'border-zinc-200'}`}
      data-testid="product-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {highlight && <span className="mb-2 inline-block rounded-md bg-zinc-900 px-2 py-0.5 text-[11px] font-medium text-white">Best match</span>}
          <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-zinc-900">{product.name}</h3>
          <p className="mt-1 text-xs text-zinc-500">
            {product.brand} · {product.rating > 0 ? `${product.rating}★ (${product.review_count.toLocaleString('en-IN')})` : 'No ratings'}
          </p>
          <p className="mt-1.5 flex items-center gap-2 text-xs">
            {product.source && <span className="chip">{SOURCE_LABEL[product.source] ?? product.source}</span>}
            {product.url.startsWith('http') && (
              <a href={product.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                View listing ↗
              </a>
            )}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-base font-semibold text-zinc-900">{inr(product.price)}</div>
          {product.suitability != null && <div className="text-xs font-medium text-emerald-600">{Math.round(product.suitability)}% match</div>}
        </div>
      </div>

      {product.suitability != null && (
        <div className="h-1 overflow-hidden rounded-full bg-zinc-100">
          <div className="h-full rounded-full bg-zinc-900" style={{ width: `${product.suitability}%` }} />
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {specChips(product).map((s) => (
          <span key={s} className="chip">
            {s}
          </span>
        ))}
      </div>

      {actionLabel && (
        <button className="btn-ghost mt-auto" onClick={onAction} disabled={disabled}>
          {actionLabel}
        </button>
      )}
    </article>
  )
}
