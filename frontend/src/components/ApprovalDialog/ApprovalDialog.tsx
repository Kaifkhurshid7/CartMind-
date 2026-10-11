import { inr } from '../../services/shopping'
import type { Recommendation } from '../../types/shopping'

interface Props {
  recommendation: Partial<Recommendation>
  priceChange?: { old: number; new: number }
  busy: boolean
  onApprove: () => void
  onCancel: () => void
}

/** Explicit human approval gate. Nothing happens in the browser until "Add to Cart" is clicked here. */
export default function ApprovalDialog({ recommendation, priceChange, busy, onApprove, onCancel }: Props) {
  const product = recommendation.product
  if (!product) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true">
      <div className="card w-full max-w-md space-y-4">
        <h2 className="text-lg font-bold text-white">{priceChange ? 'Price changed' : 'CartMind Recommendation'}</h2>

        <div>
          <p className="font-semibold text-white">{product.name}</p>
          {priceChange ? (
            <p className="text-sm text-amber-300">
              The price changed from <s>{inr(priceChange.old)}</s> to <strong>{inr(priceChange.new)}</strong>. Do you still
              want me to continue?
            </p>
          ) : (
            <p className="text-xl font-bold text-white">{inr(product.price)}</p>
          )}
        </div>

        {!priceChange && (
          <>
            <ul className="space-y-1 text-sm text-slate-300">
              {(recommendation.reasons ?? []).slice(0, 5).map((r) => (
                <li key={r}>
                  <span className="mr-2 text-emerald-400">✓</span>
                  {r}
                </li>
              ))}
            </ul>
            {recommendation.summary && (
              <p className="rounded-xl bg-white/5 p-3 text-sm text-slate-300">
                <span className="font-semibold text-white">Why this product? </span>
                {recommendation.summary}
              </p>
            )}
          </>
        )}

        <p className="text-xs text-slate-500">CartMind will add this to your cart and stop before payment.</p>

        <div className="flex gap-3">
          <button className="btn-primary flex-1" onClick={onApprove} disabled={busy}>
            {priceChange ? 'Continue anyway' : 'Add to Cart'}
          </button>
          <button className="btn-ghost flex-1" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
