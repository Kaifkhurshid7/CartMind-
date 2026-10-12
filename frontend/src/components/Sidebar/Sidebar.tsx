import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import type { Health } from '../../hooks/useHealth'
import { listSessions } from '../../services/shopping'
import { timeAgo } from '../../services/time'
import type { SessionSummary } from '../../types/shopping'
import { BagIcon, ChatIcon, GearIcon, InfoIcon, ListIcon, LogoMark, SidebarIcon } from '../icons'

type Tab = 'chats' | 'info' | 'settings'

const DOT: Record<string, string> = {
  started: 'bg-blue-500',
  running: 'bg-blue-500',
  executing: 'bg-blue-500',
  waiting_for_approval: 'bg-amber-500',
  waiting_for_user: 'bg-amber-500',
  price_changed: 'bg-amber-500',
  completed: 'bg-emerald-500',
  failed: 'bg-rose-500',
  no_results: 'bg-rose-400',
  cancelled: 'bg-zinc-300',
  needs_clarification: 'bg-amber-400',
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-start justify-between gap-3 py-2 text-[13px]">
      <span className="text-zinc-500">{k}</span>
      <span className="text-right font-medium text-zinc-800">{v}</span>
    </div>
  )
}

export default function Sidebar({ health, onCollapse }: { health: Health | null; onCollapse: () => void }) {
  const [tab, setTab] = useState<Tab>('chats')
  const [items, setItems] = useState<SessionSummary[]>([])
  const { id: activeId } = useParams()
  const { pathname } = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    let alive = true
    const load = () =>
      listSessions()
        .then((r) => alive && setItems(r.slice(0, 30)))
        .catch(() => undefined)
    load()
    const t = setInterval(load, 8000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [pathname])

  const tabBtn = (t: Tab, label: string, icon: JSX.Element) => (
    <button
      key={t}
      aria-label={label}
      title={label}
      aria-pressed={tab === t}
      onClick={() => setTab(t)}
      className={`flex h-8 w-9 items-center justify-center rounded-lg transition ${
        tab === t ? 'bg-white text-zinc-900 shadow-sm ring-1 ring-zinc-200' : 'text-zinc-400 hover:text-zinc-700'
      }`}
    >
      {icon}
    </button>
  )

  return (
    <aside className="hidden w-[260px] shrink-0 flex-col border-r border-zinc-200/80 bg-[#f6f6f4] px-4 py-4 md:flex">
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 text-[17px] font-semibold tracking-tight text-zinc-900">
          <LogoMark />
          CartMind
        </Link>
        <button className="icon-btn" aria-label="Collapse sidebar" onClick={onCollapse}>
          <SidebarIcon />
        </button>
      </div>

      <div className="mt-4 border-t border-zinc-200 pt-4">
        <div className="flex gap-1">
          {tabBtn('chats', 'Searches', <ListIcon />)}
          {tabBtn('info', 'How it works', <InfoIcon />)}
          {tabBtn('settings', 'Settings', <GearIcon />)}
        </div>
      </div>

      <button
        onClick={() => navigate('/')}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-700"
      >
        <ChatIcon width={15} height={15} />
        New Chat
      </button>

      <div className="mt-5 min-h-0 flex-1 overflow-y-auto">
        {tab === 'chats' && (
          <>
            <p className="mb-2 text-[13px] text-zinc-500">Recent searches</p>
            {items.length === 0 && <p className="px-1 text-[13px] text-zinc-400">Nothing yet. Start a new chat.</p>}
            <ul className="space-y-0.5">
              {items.map((s) => (
                <li key={s.id}>
                  <Link
                    to={`/session/${s.id}`}
                    title={`${s.query} · ${timeAgo(s.created_at)}`}
                    className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[14px] transition ${
                      s.id === activeId ? 'bg-zinc-200/70 font-medium text-zinc-900' : 'text-zinc-700 hover:bg-zinc-200/40'
                    }`}
                  >
                    <BagIcon width={15} height={15} className="shrink-0 text-zinc-400" />
                    <span className="min-w-0 flex-1 truncate">{s.query}</span>
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[s.status] ?? 'bg-zinc-300'}`} aria-label={s.status} />
                  </Link>
                </li>
              ))}
            </ul>
            {items.length > 0 && (
              <Link to="/history" className="mt-3 block px-2.5 text-[13px] text-zinc-500 hover:text-zinc-800">
                View all
              </Link>
            )}
          </>
        )}

        {tab === 'info' && (
          <div className="space-y-4 text-[13px] leading-relaxed text-zinc-600">
            <div>
              <p className="mb-1 font-medium text-zinc-900">How it works</p>
              <ol className="list-decimal space-y-1 pl-4">
                <li>Describe what you want.</li>
                <li>An AI-driven browser researches real listings.</li>
                <li>You get a ranked recommendation with reasons.</li>
                <li>You approve; it adds the item to your cart.</li>
                <li>It re-opens the cart to verify.</li>
              </ol>
            </div>
            <div>
              <p className="mb-1 font-medium text-zinc-900">Safety</p>
              <ul className="list-disc space-y-1 pl-4">
                <li>Never buys or pays; stops at the cart.</li>
                <li>Asks before every action.</li>
                <li>Never types passwords or solves CAPTCHAs.</li>
              </ul>
            </div>
          </div>
        )}

        {tab === 'settings' && (
          <div className="divide-y divide-zinc-200">
            <Row k="Mode" v={health?.shopping_mode ?? '…'} />
            <Row k="Model" v={health?.llm_model ?? (health ? 'none (rule-based)' : '…')} />
            <Row k="Shop" v={health?.site ?? '…'} />
            <Row k="AI key" v={health ? (health.llm_configured ? 'Configured' : 'Missing') : '…'} />
            <p className="pt-3 text-xs leading-relaxed text-zinc-500">
              Settings come from the backend <code>.env</code> file. Run <code>python login.py</code> once to sign in to your shopping accounts.
            </p>
          </div>
        )}
      </div>

      <div className="mt-3 border-t border-zinc-200 pt-3">
        <button
          onClick={() => setTab('settings')}
          className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[14px] text-zinc-600 hover:bg-zinc-200/40"
        >
          <GearIcon width={15} height={15} />
          Settings
        </button>
        <div className="mt-2 flex items-center gap-3 px-1">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-300 text-sm font-semibold text-zinc-700">C</span>
          <span className="min-w-0 text-[13px] leading-tight">
            <span className="block truncate font-medium text-zinc-800">Local workspace</span>
            <span className="block truncate text-zinc-500">{health?.site ?? 'CartMind'}</span>
          </span>
        </div>
      </div>
    </aside>
  )
}
