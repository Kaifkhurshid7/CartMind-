import { inr } from '../../services/shopping'
import { CheckIcon, ExternalIcon, XIcon } from '../icons'
import type { ShoppingSession } from '../../types/shopping'

export default function CartStatus({ session }: { session: ShoppingSession }) {
  const { status, cart_state: cart } = session

  if (status === 'completed') {
    const items = cart.items ?? []
    const total = cart.total ?? items.reduce((sum, i) => sum + (i.price ?? 0), 0)

    return (
      <section className="animate-fade-up overflow-hidden rounded-card border border-line bg-white shadow-soft" data-testid="cart-success">
        <header className="flex items-center gap-3 border-b border-line px-5 py-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-50 text-green-700">
            <CheckIcon width={16} height={16} strokeWidth={2.4} />
          </span>
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold leading-5 text-fg">Added to your cart</h2>
            <p className="text-[13px] leading-5 text-fg-3">CartMind stopped before payment. Checkout is up to you.</p>
          </div>
        </header>

        <ul className="divide-y divide-line px-5">
          {items.map((i) => (
            <li key={i.product_id} className="flex items-start justify-between gap-4 py-3">
              <span className="line-clamp-2 min-w-0 break-words text-[14px] leading-5 text-fg" title={i.name}>
                {i.name}
              </span>
              <span className="shrink-0 text-[14px] font-medium tabular-nums text-fg">{inr(i.price)}</span>
            </li>
          ))}
        </ul>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-zinc-50/60 px-5 py-3">
          <p className="text-[13px] text-fg-2">
            {items.length > 1 ? `Total (${items.length} items)` : 'Total'}
            <span className="ml-2 text-[15px] font-semibold tabular-nums text-fg">{inr(total)}</span>
          </p>
          {cart.url && (
            <a className="btn-primary h-10 px-4" href={cart.url} target="_blank" rel="noreferrer">
              Open cart
              <ExternalIcon width={14} height={14} />
            </a>
          )}
        </footer>
      </section>
    )
  }
  if (status === 'failed' || status === 'cancelled') {
    const cancelled = status === 'cancelled'
    return (
      <section className="animate-fade-up flex items-start gap-3 rounded-card border border-line bg-white px-5 py-4 shadow-soft">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${cancelled ? 'bg-zinc-100 text-zinc-600' : 'bg-rose-50 text-rose-700'}`}>
          <XIcon width={16} height={16} strokeWidth={2.4} />
        </span>
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold leading-5 text-fg">{cancelled ? 'Cancelled' : 'Could not complete'}</h2>
          <p className="mt-0.5 break-words text-[13px] leading-5 text-fg-2">
            {cancelled ? 'Nothing was added to your cart.' : (session.error ?? 'Something went wrong.')}
          </p>
        </div>
      </section>
    )
  }
  return null
}
