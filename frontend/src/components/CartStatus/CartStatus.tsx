import { inr } from '../../services/shopping'
import type { ShoppingSession } from '../../types/shopping'

export default function CartStatus({ session }: { session: ShoppingSession }) {
  const { status, cart_state: cart } = session

  if (status === 'executing') {
    return (
      <section className="card border-brand-500/40">
        <h2 className="font-semibold text-white">Shopping Agent</h2>
        <p className="mt-1 animate-pulse text-sm text-slate-300">Operating the browser — searching, verifying and adding to cart…</p>
      </section>
    )
  }
  if (status === 'completed') {
    return (
      <section className="card border-emerald-500/40 bg-emerald-500/5" data-testid="cart-success">
        <h2 className="font-semibold text-emerald-300">✅ Product successfully added to cart</h2>
        <ul className="mt-2 space-y-1 text-sm text-slate-300">
          {(cart.items ?? []).map((i) => (
            <li key={i.product_id} className="flex justify-between gap-4">
              <span>{i.name}</span>
              <span>{inr(i.price)}</span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-400">CartMind stopped before payment — checkout is up to you.</p>
        {cart.url && (
          <a className="btn-ghost mt-3" href={cart.url} target="_blank" rel="noreferrer">
            Open store cart ↗
          </a>
        )}
      </section>
    )
  }
  if (status === 'failed' || status === 'cancelled') {
    return (
      <section className="card border-rose-500/30">
        <h2 className="font-semibold text-rose-300">{status === 'cancelled' ? 'Cancelled' : 'Could not complete'}</h2>
        <p className="mt-1 text-sm text-slate-300">
          {status === 'cancelled' ? 'Nothing was added to your cart.' : (session.error ?? 'Something went wrong.')}
        </p>
      </section>
    )
  }
  return null
}
