import { inr } from '../../services/shopping'
import { CheckIcon } from '../icons'
import type { Recommendation } from '../../types/shopping'

interface Props {
  recommendation: Partial<Recommendation>
  priceChange?: { old: number; new: number }
  busy: boolean
  onApprove: () => void
  onCancel: () => void
}

/**
 * Inline human-approval gate, shown at the end of the thread.
 * Nothing happens in the browser until "Add to Cart" is clicked here.
 */
export default function ApprovalDialog({ recommendation, priceChange, busy, onApprove, onCancel }: Props) {
  const product = recommendation.product
  if (!product) return null

  return (
    <section
      className="rounded-xl border border-zinc-900 bg-white p-4 shadow-sm"
      role="region"
      aria-label={priceChange ? 'Price changed' : 'Approval needed'}
      data-testid="approval"
    >
      <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">
        {priceChange ? 'Price changed — confirm to continue' : 'Approval needed'}
      </p>
      <p className="mt-1 text-sm font-semibold text-zinc-900">{product.name}</p>

      {priceChange ? (
        <p className="mt-1 text-sm text-amber-700">
          The price changed from <s>{inr(priceChange.old)}</s> to <strong>{inr(priceChange.new)}</strong>. Do you still want me to
          continue?
        </p>
      ) : (
        <>
          <p className="text-lg font-semibold text-zinc-900">{inr(product.price)}</p>
          <ul className="mt-2 space-y-1 text-[13px] text-zinc-600">
            {(recommendation.reasons ?? []).slice(0, 4).map((r) => (
              <li key={r} className="flex gap-2">
                <CheckIcon width={14} height={14} className="mt-0.5 shrink-0 text-emerald-600" />
                {r}
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="mt-3 text-xs text-zinc-400">CartMind will add this to the cart and stop before payment.</p>
      <div className="mt-3 flex gap-2">
        <button className="btn-primary" onClick={onApprove} disabled={busy}>
          {priceChange ? 'Continue anyway' : 'Add to Cart'}
        </button>
        <button className="btn-ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </section>
  )
}
