import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import AgentActivity from '../components/AgentActivity/AgentActivity'
import ApprovalDialog from '../components/ApprovalDialog/ApprovalDialog'
import CartStatus from '../components/CartStatus/CartStatus'
import { AgentMessage, DayDivider, Thinking, UserMessage } from '../components/Chat/Chat'
import Composer from '../components/Chat/Composer'
import { FOLLOW_UP_PROMPTS, STARTER_PROMPTS } from '../components/Chat/PromptLibrary'
import ProductCard, { CompactCard } from '../components/ProductCard/ProductCard'
import ProductComparison from '../components/ProductComparison/ProductComparison'
import Shell from '../components/Shell/Shell'
import UserAction from '../components/UserAction/UserAction'
import { useShoppingSession } from '../hooks/useShoppingSession'
import { errorMessage } from '../services/api'
import { approve, cancelSession, continueSession, inr, sendChat } from '../services/shopping'
import { dayLabel } from '../services/time'
import type { Product } from '../types/product'
import type { Comparison, Recommendation, ShoppingSession as Session } from '../types/shopping'

const CHIPS = ['Why did you choose this one?', 'Show me a cheaper alternative', 'Which option has the best reviews?']

function RecommendationBlock({
  rec,
  comparison,
  latest,
  canChoose,
  onChoose,
}: {
  rec: Partial<Recommendation>
  comparison?: Comparison
  latest: boolean
  canChoose: boolean
  onChoose: (p: Product) => void
}) {
  if (!rec.product) return null
  return (
    <>
      <ProductCard product={rec.product} highlight />
      {latest && (
        <>
          <div className="grid gap-4 rounded-xl border border-zinc-200 p-4 text-[13px] sm:grid-cols-2">
            <div>
              <h3 className="mb-1.5 font-semibold text-zinc-900">Why this product</h3>
              <ul className="space-y-1 text-zinc-600">
                {(rec.reasons ?? []).map((r) => (
                  <li key={r}>✓ {r}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-1.5 font-semibold text-zinc-900">Trade-offs</h3>
              <ul className="space-y-1 text-zinc-600">
                {(rec.disadvantages ?? []).map((d) => (
                  <li key={d}>• {d}</li>
                ))}
              </ul>
            </div>
          </div>
          {comparison && <ProductComparison comparison={comparison} selectedId={rec.product.id} />}
          {(rec.alternatives ?? []).length > 0 && (
            <div>
              <h3 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-zinc-400">Other options</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                {(rec.alternatives ?? []).slice(0, 3).map((p, i) => (
                  <CompactCard
                    key={p.id}
                    product={p}
                    index={i}
                    actionLabel={canChoose ? 'Choose this instead' : undefined}
                    onAction={() => onChoose(p)}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}

export default function ShoppingSession() {
  const { id } = useParams()
  const { session, events, error, refresh } = useShoppingSession(id)
  const [alternative, setAlternative] = useState<Product | null>(null)
  const [acting, setActing] = useState(false)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const status = session?.status
  const awaiting = status === 'waiting_for_approval' || status === 'price_changed'
  const needsUser = status === 'waiting_for_user'
  const busy = status === 'running' || status === 'started' || status === 'executing' || needsUser

  useEffect(() => {
    if (!awaiting) setAlternative(null)
  }, [awaiting])

  const msgCount = session?.messages.length ?? 0
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [msgCount, events.length, status, awaiting])

  const lastRecIndex = useMemo(() => {
    const msgs = session?.messages ?? []
    for (let i = msgs.length - 1; i >= 0; i--) if (msgs[i].meta?.type === 'recommendation') return i
    return -1
  }, [session?.messages])

  async function run(action: () => Promise<unknown>) {
    setActing(true)
    setActionError(null)
    try {
      await action()
      await refresh()
    } catch (e) {
      setActionError(errorMessage(e))
    } finally {
      setActing(false)
    }
  }

  async function submit(override?: string) {
    const message = (override ?? text).trim()
    if (!id || !message || sending) return
    setSending(true)
    if (override === undefined) setText('')
    setActionError(null)
    try {
      await sendChat(id, message)
      await refresh()
    } catch (e) {
      setActionError(errorMessage(e))
    } finally {
      setSending(false)
    }
  }

  if (error && !session) {
    return (
      <Shell>
        <p className="p-8 text-rose-600">{error}</p>
      </Shell>
    )
  }
  if (!session || !id) {
    return (
      <Shell>
        <p className="p-8 text-zinc-500">Loading session…</p>
      </Shell>
    )
  }

  const rec = session.recommendation
  const chosen = alternative ?? rec?.product
  const approvalRec: Partial<Recommendation> | undefined = alternative
    ? { product: alternative, reasons: ['You chose this instead of the top pick'], summary: '' }
    : rec
  const lastEvent = events[events.length - 1]?.message

  const thread: JSX.Element[] = []
  let lastDay = ''
  session.messages.forEach((m, i) => {
    const day = dayLabel(m.timestamp)
    if (day !== lastDay) {
      thread.push(<DayDivider key={`d${i}`} label={day} />)
      lastDay = day
    }
    const isLatestRec = i === lastRecIndex
    thread.push(
      <div key={`m${i}`} className="mb-5">
        {m.role === 'user' ? (
          <UserMessage text={m.content} at={m.timestamp} />
        ) : (
          <AgentMessage
            id={`${id}:${i}`}
            text={m.content}
            at={m.timestamp}
            chips={isLatestRec && !busy ? CHIPS : undefined}
            onChip={(c) => void submit(c)}
          >
            {m.meta?.type === 'recommendation' && m.meta.recommendation && (
              <RecommendationBlock
                rec={m.meta.recommendation}
                comparison={isLatestRec ? session.comparison : m.meta.comparison}
                latest={isLatestRec}
                canChoose={status === 'waiting_for_approval'}
                onChoose={setAlternative}
              />
            )}
          </AgentMessage>
        )}
        {i === 0 && events.length > 0 && (
          <div className="mt-5">
            <AgentActivity events={events} status={status} />
          </div>
        )}
      </div>,
    )
  })

  const footer = (
    <div className="shrink-0 px-4 pb-4 pt-1 sm:px-6">
      <div className="mx-auto w-full max-w-[760px]">
        <Composer
          value={text}
          onChange={setText}
          onSubmit={() => void submit()}
          prompts={rec?.product ? FOLLOW_UP_PROMPTS : STARTER_PROMPTS}
          disabled={busy}
          sending={sending}
          placeholder={busy ? 'CartMind is working…' : 'Ask me anything'}
        />
      </div>
    </div>
  )

  return (
    <Shell footer={footer} control={{ busy, onCancel: () => void run(() => cancelSession(id)) }}>
      <div className="flex-1 overflow-y-auto px-4 pb-4 sm:px-6">
        <div className="mx-auto w-full max-w-[760px]">
          {thread.map((el, i) => (
            <Fragment key={i}>{el}</Fragment>
          ))}

          {status === 'no_results' && session.near_misses.length > 0 && (
            <div className="mb-5 space-y-3 rounded-2xl border border-zinc-200 bg-white p-5">
              <p className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">Closest options</p>
              <div className="grid gap-3 sm:grid-cols-3">
                {session.near_misses.map((n, i) => (
                  <div key={n.product.id}>
                    <CompactCard product={n.product} index={i} />
                    <p className="mt-1 text-xs text-amber-700">Misses: {n.fails}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {needsUser && (
            <div className="mb-5">
              <UserAction
                message={session.user_prompt ?? 'Please complete the step in the browser window.'}
                busy={acting}
                onContinue={() => run(() => continueSession(id))}
                onCancel={() => run(() => cancelSession(id))}
              />
            </div>
          )}

          {awaiting && approvalRec && chosen && (
            <div className="mb-5">
              <ApprovalDialog
                recommendation={approvalRec}
                priceChange={status === 'price_changed' ? (session.price_change ?? undefined) : undefined}
                busy={acting}
                onApprove={() => run(() => approve(id, chosen.id, status === 'price_changed'))}
                onCancel={() => run(() => cancelSession(id))}
              />
              {alternative && (
                <button className="mt-2 text-xs text-blue-600 hover:underline" onClick={() => setAlternative(null)}>
                  Back to the top pick ({inr(rec.product?.price)})
                </button>
              )}
            </div>
          )}

          <div className="mb-5">
            <CartStatus session={session as Session} />
          </div>

          {busy && !needsUser && (
            <div className="mb-5">
              <Thinking detail={lastEvent} />
            </div>
          )}
          {actionError && <p className="mb-4 text-sm text-rose-600">{actionError}</p>}
          <div ref={bottomRef} />
        </div>
      </div>
    </Shell>
  )
}
