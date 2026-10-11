import { inr } from '../../services/shopping'
import type { ShoppingSession } from '../../types/shopping'

export default function CartStatus({ session }: { session: ShoppingSession }) {
  const { status, cart_state: cart } = session

  if (status === 'completed') {
    return (
      <section className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4" data-testid="cart-success">
        <h2 className="text-sm font-semibold text-emerald-800">✓ Product successfully added to cart</h2>
        <ul className="mt-2 space-y-1 text-[13px] text-zinc-700">
          {(cart.items ?? []).map((i) => (
            <li key={i.product_id} className="flex justify-between gap-4">
              <span className="truncate">{i.name}</span>
              <span className="shrink-0">{inr(i.price)}</span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-zinc-500">CartMind stopped before payment — checkout is up to you.</p>
        {cart.url && (
          <a className="btn-ghost mt-3" href={cart.url} target="_blank" rel="noreferrer">
            Open cart ↗
          </a>
        )}
      </section>
    )
  }
  if (status === 'failed' || status === 'cancelled') {
    return (
      <section className="rounded-xl border border-rose-200 bg-rose-50/60 p-4">
        <h2 className="text-sm font-semibold text-rose-800">{status === 'cancelled' ? 'Cancelled' : 'Could not complete'}</h2>
        <p className="mt-1 text-[13px] text-zinc-700">
          {status === 'cancelled' ? 'Nothing was added to your cart.' : (session.error ?? 'Something went wrong.')}
        </p>
      </section>
    )
  }
  return null
}
