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
}

export function specChips(p: Product): string[] {
  return Object.entries(p.specs)
    .map(([k, v]) => SPEC_LABEL[k]?.(v) ?? null)
    .filter((x): x is string => !!x)
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
      className={`card flex flex-col gap-3 ${highlight ? 'border-brand-500/60 ring-1 ring-brand-500/40' : ''}`}
      data-testid="product-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          {highlight && <span className="chip mb-2 bg-brand-500/20 text-brand-400">🏆 Best match</span>}
          <h3 className="font-semibold text-white">{product.name}</h3>
          <p className="text-xs text-slate-400">
            {product.brand} · {product.rating}★ ({product.review_count.toLocaleString('en-IN')} reviews)
          </p>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-white">{inr(product.price)}</div>
          {product.suitability != null && <div className="text-xs text-emerald-400">{Math.round(product.suitability)}% match</div>}
        </div>
      </div>

      {product.suitability != null && (
        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
          <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-emerald-400" style={{ width: `${product.suitability}%` }} />
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
