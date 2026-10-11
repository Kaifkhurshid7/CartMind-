import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AgentActivity from '../components/AgentActivity/AgentActivity'
import ApprovalDialog from '../components/ApprovalDialog/ApprovalDialog'
import CartStatus from '../components/CartStatus/CartStatus'
import Chat from '../components/Chat/Chat'
import ProductCard from '../components/ProductCard/ProductCard'
import ProductComparison from '../components/ProductComparison/ProductComparison'
import { useShoppingSession } from '../hooks/useShoppingSession'
import { errorMessage } from '../services/api'
import { approve, cancelSession, inr } from '../services/shopping'
import type { Product } from '../types/product'
import type { Recommendation } from '../types/shopping'

export default function ShoppingSession() {
  const { id } = useParams()
  const { session, events, error, refresh } = useShoppingSession(id)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [alternative, setAlternative] = useState<Product | null>(null)
  const [acting, setActing] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const status = session?.status
  const awaiting = status === 'waiting_for_approval' || status === 'price_changed'
  useEffect(() => {
    if (awaiting) setDialogOpen(true)
    else {
      setDialogOpen(false)
      setAlternative(null)
    }
  }, [awaiting, session?.recommendation?.product?.id])

  const rec = session?.recommendation
  const dialogRec: Partial<Recommendation> | undefined = useMemo(() => {
    if (alternative) return { product: alternative, reasons: [], summary: `You chose ${alternative.name} instead of the top pick.` }
    return rec
  }, [alternative, rec])

  async function run(action: () => Promise<unknown>) {
    setActing(true)
    setActionError(null)
    try {
      await action()
      setDialogOpen(false)
      await refresh()
    } catch (e) {
      setActionError(errorMessage(e))
    } finally {
      setActing(false)
    }
  }

  if (error && !session) return <p className="text-rose-400">{error}</p>
  if (!session || !id) return <p className="animate-pulse text-slate-400">Loading session…</p>

  const req = session.requirements
  const chosen = dialogRec?.product ?? rec?.product
  const others = (session.shortlisted_products ?? []).filter((p) => p.id !== rec?.product?.id)
  const chatLocked = status === 'running' || status === 'started' || status === 'executing'

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
      <div className="space-y-6">
        <header className="space-y-3">
          <Link to="/" className="text-sm text-brand-400 hover:underline">
            ← New search
          </Link>
          <h1 className="text-xl font-bold text-white">{session.query}</h1>
          <div className="flex flex-wrap gap-2">
            {req.category && <span className="chip">📦 {req.category}</span>}
            {req.budget?.maximum != null && <span className="chip">💰 ≤ {inr(req.budget.maximum)}</span>}
            {req.use_case && <span className="chip">🎯 {req.use_case}</span>}
            {Object.entries(req.requirements ?? {}).map(([k, v]) => (
              <span key={k} className="chip">
                {k}: {v}
              </span>
            ))}
            {(req.priorities ?? []).map((p) => (
              <span key={p} className="chip bg-brand-500/20 text-brand-400">
                ★ {p}
              </span>
            ))}
            {session.search_count > 0 && (
              <span className="chip">
                {session.search_count} found · {session.shortlisted_products.length} shortlisted
              </span>
            )}
          </div>
        </header>

        <CartStatus session={session} />
        {actionError && <p className="text-sm text-rose-400">{actionError}</p>}

        {session.status === 'needs_clarification' && (
          <section className="card border-amber-400/40">
            <p className="text-amber-200">{session.error}</p>
            <p className="mt-1 text-sm text-slate-400">Reply in the chat on the right to continue.</p>
          </section>
        )}

        {session.status === 'no_results' && (
          <section className="card space-y-3 border-rose-400/30">
            <h2 className="font-semibold text-rose-300">No product meets every requirement</h2>
            {session.near_misses.length > 0 ? (
              <>
                <p className="text-sm text-slate-300">Closest options — each misses just one requirement:</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {session.near_misses.map((n) => (
                    <div key={n.product.id}>
                      <ProductCard product={n.product} />
                      <p className="mt-1 text-xs text-amber-300">Misses: {n.fails}</p>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-slate-400">Tell me in the chat what to relax (e.g. “raise the budget to ₹55k”).</p>
              </>
            ) : (
              <p className="text-sm text-slate-300">Try raising the budget or relaxing a spec in the chat.</p>
            )}
          </section>
        )}

        {rec?.product && (
          <section className="space-y-4">
            <ProductCard product={rec.product} highlight />
            <div className="card space-y-3 text-sm">
              <p className="leading-relaxed text-slate-200">{rec.summary}</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="mb-1 font-semibold text-emerald-400">Why this product</h3>
                  <ul className="space-y-1 text-slate-300">
                    {(rec.reasons ?? []).map((r) => (
                      <li key={r}>✓ {r}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-amber-300">Trade-offs</h3>
                  <ul className="space-y-1 text-slate-300">
                    {(rec.disadvantages ?? []).map((d) => (
                      <li key={d}>• {d}</li>
                    ))}
                  </ul>
                </div>
              </div>
              {rec.alternative_note && <p className="text-slate-400">{rec.alternative_note}</p>}
              {awaiting && !dialogOpen && (
                <button className="btn-primary" onClick={() => setDialogOpen(true)}>
                  Review &amp; approve
                </button>
              )}
            </div>
          </section>
        )}

        <ProductComparison comparison={session.comparison} selectedId={rec?.product?.id} />

        {others.length > 0 && (
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Other options</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {others.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  actionLabel={status === 'waiting_for_approval' ? 'Choose this instead' : undefined}
                  onAction={() => {
                    setAlternative(p)
                    setDialogOpen(true)
                  }}
                />
              ))}
            </div>
          </section>
        )}
      </div>

      <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
        <AgentActivity events={events} status={status} />
        <Chat sessionId={id} messages={session.messages} disabled={chatLocked} onAction={(a) => { if (a === 'request_approval') setDialogOpen(true); void refresh() }} />
      </aside>

      {dialogOpen && awaiting && dialogRec && chosen && (
        <ApprovalDialog
          recommendation={dialogRec}
          priceChange={status === 'price_changed' ? session.price_change : undefined}
          busy={acting}
          onApprove={() => run(() => approve(id, chosen.id, status === 'price_changed'))}
          onCancel={() => run(() => cancelSession(id))}
        />
      )}
    </div>
  )
}
