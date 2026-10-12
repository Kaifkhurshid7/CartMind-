import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom'
import type { Health } from '../../hooks/useHealth'
import { groupByDate, hideSession, renameSession, useSessionPrefs } from '../../services/sessionPrefs'
import { listSessions } from '../../services/shopping'
import type { SessionSummary } from '../../types/shopping'
import { ClockIcon, GearIcon, HomeIcon, LogoMark, PlusIcon, SearchIcon, SidebarIcon } from '../icons'
import Popover from '../ui/Popover'
import HistoryItem from './HistoryItem'

interface Props {
  health: Health | null
  /** Icon-only rail (desktop). */
  rail: boolean
  onToggleRail: () => void
  /** Closes the mobile drawer after navigating. */
  onNavigate: () => void
}

const navCls = (active: boolean, rail: boolean) =>
  `flex h-9 items-center gap-3 rounded-lg text-[14px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/30 ${
    rail ? 'w-9 justify-center' : 'px-3'
  } ${active ? 'bg-zinc-200/70 font-medium text-zinc-900' : 'text-zinc-600 hover:bg-zinc-200/40 hover:text-zinc-900'}`

function SectionLabel({ children }: { children: string }) {
  return <p className="px-3 pb-1 pt-4 text-[12px] font-medium uppercase tracking-wider text-zinc-400">{children}</p>
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 text-[13px]">
      <span className="text-zinc-500">{k}</span>
      <span className="text-right font-medium text-zinc-800">{v}</span>
    </div>
  )
}

export default function Sidebar({ health, rail, onToggleRail, onNavigate }: Props) {
  const [items, setItems] = useState<SessionSummary[]>([])
  const [search, setSearch] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { id: activeId } = useParams()
  const navigate = useNavigate()
  const prefs = useSessionPrefs()
  const closeSettings = useCallback(() => setSettingsOpen(false), [])

  useEffect(() => {
    let alive = true
    const load = () =>
      listSessions()
        .then((r) => alive && setItems(r))
        .catch(() => undefined)
    load()
    const t = setInterval(load, 8000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [activeId])

  const titleOf = useCallback((s: SessionSummary) => prefs.titles[s.id] ?? s.query, [prefs.titles])

  const groups = useMemo(() => {
    const q = search.trim().toLowerCase()
    const visible = items.filter((s) => !prefs.hidden.includes(s.id) && (!q || titleOf(s).toLowerCase().includes(q)))
    return groupByDate(visible.slice(0, 100))
  }, [items, prefs.hidden, search, titleOf])

  const hasAny = items.some((s) => !prefs.hidden.includes(s.id))
  const newChat = () => {
    navigate('/')
    onNavigate()
  }

  return (
    <div className={`flex h-full min-h-0 flex-col bg-[#f7f7f5] py-3 ${rail ? 'items-center px-3' : 'px-3'}`}>
      {/* Brand */}
      <div className={`flex h-10 w-full items-center ${rail ? 'justify-center' : 'justify-between px-1'}`}>
        {rail ? (
          <button className="icon-btn !h-9 !w-9" aria-label="Expand sidebar" title="Expand sidebar" onClick={onToggleRail}>
            <SidebarIcon width={18} height={18} />
          </button>
        ) : (
          <>
            <Link
              to="/"
              onClick={onNavigate}
              className="flex items-center gap-2.5 rounded-lg text-[18px] font-semibold tracking-tight text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/30"
            >
              <LogoMark />
              CartMind
            </Link>
            <button className="icon-btn hidden md:inline-flex" aria-label="Collapse sidebar" title="Collapse sidebar" onClick={onToggleRail}>
              <SidebarIcon />
            </button>
          </>
        )}
      </div>
      <div className="my-3 h-px w-full bg-zinc-200" />

      {/* Primary action */}
      <button
        onClick={newChat}
        aria-label="New shopping session"
        title={rail ? 'New shopping session' : undefined}
        className={`flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl bg-zinc-900 text-[14px] font-medium text-white transition hover:bg-zinc-700 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/40 focus-visible:ring-offset-2 ${
          rail ? 'w-10' : 'w-full'
        }`}
      >
        <PlusIcon width={16} height={16} />
        {!rail && 'New shopping session'}
      </button>

      {/* Workspace */}
      {!rail && <SectionLabel>Workspace</SectionLabel>}
      <nav className={`flex flex-col gap-0.5 ${rail ? 'mt-3 items-center' : 'w-full'}`} aria-label="Workspace">
        <NavLink to="/" end onClick={onNavigate} title="Home" aria-label="Home" className={({ isActive }) => navCls(isActive, rail)}>
          <HomeIcon width={18} height={18} className="shrink-0" />
          {!rail && 'Home'}
        </NavLink>
        <NavLink to="/history" onClick={onNavigate} title="All searches" aria-label="All searches" className={({ isActive }) => navCls(isActive, rail)}>
          <ClockIcon width={18} height={18} className="shrink-0" />
          {!rail && 'All searches'}
        </NavLink>
      </nav>

      {/* History: the only scrolling region */}
      {!rail ? (
        <div className="flex min-h-0 w-full flex-1 flex-col">
          <SectionLabel>History</SectionLabel>
          <label className="mb-2 flex h-9 shrink-0 items-center gap-2 rounded-lg border border-zinc-200 bg-white px-3 text-zinc-400 focus-within:border-zinc-300 focus-within:ring-2 focus-within:ring-zinc-900/10">
            <SearchIcon width={15} height={15} className="shrink-0" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations"
              aria-label="Search conversations"
              className="min-w-0 flex-1 bg-transparent text-[14px] text-zinc-900 outline-none placeholder:text-zinc-400"
            />
          </label>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {groups.length === 0 && (
              <p className="px-3 py-2 text-[13px] text-zinc-500">
                {hasAny ? 'No conversations match your search.' : 'No conversations yet. Start a new session.'}
              </p>
            )}
            {groups.map((g) => (
              <section key={g.label} className="mb-2">
                <h3 className="px-3 pb-1 pt-2 text-[12px] font-medium text-zinc-500">{g.label}</h3>
                <ul className="space-y-0.5">
                  {g.items.map((s) => (
                    <li key={s.id}>
                      <HistoryItem
                        session={s}
                        title={titleOf(s)}
                        active={s.id === activeId}
                        onNavigate={onNavigate}
                        onRename={(t) => renameSession(s.id, t)}
                        onDelete={() => {
                          hideSession(s.id)
                          if (s.id === activeId) navigate('/')
                        }}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1" />
      )}

      {/* Bottom: settings + workspace */}
      <div className={`relative mt-2 w-full shrink-0 border-t border-zinc-200 pt-3 ${rail ? 'flex flex-col items-center gap-2' : ''}`}>
        <Popover open={settingsOpen} onClose={closeSettings} className={`bottom-full mb-2 ${rail ? 'left-0 w-64' : 'inset-x-0'}`}>
          <div className="rounded-xl border border-zinc-200 bg-white p-3 shadow-lg">
            <p className="pb-1 text-[13px] font-semibold text-zinc-900">Settings</p>
            <div className="divide-y divide-zinc-100">
              <Row k="Mode" v={health?.shopping_mode ?? '…'} />
              <Row k="Model" v={health?.llm_model ?? (health ? 'none (rule-based)' : '…')} />
              <Row k="Shop" v={health?.site ?? '…'} />
              <Row k="AI key" v={health ? (health.llm_configured ? 'Configured' : 'Missing') : '…'} />
            </div>
            <p className="pt-2 text-xs leading-relaxed text-zinc-500">
              Values come from the backend <code>.env</code>. CartMind never pays; it stops at the cart.
            </p>
          </div>
        </Popover>
        <button
          onClick={() => setSettingsOpen((o) => !o)}
          aria-haspopup="dialog"
          aria-expanded={settingsOpen}
          aria-label="Settings"
          title="Settings"
          className={`${navCls(settingsOpen, rail)} ${rail ? '' : 'w-full'}`}
        >
          <GearIcon width={18} height={18} className="shrink-0" />
          {!rail && 'Settings'}
        </button>
        <div className={`flex items-center gap-3 ${rail ? '' : 'mt-1 px-3 py-1'}`}>
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-300 text-[13px] font-semibold text-zinc-700" aria-hidden="true">
            C
          </span>
          {!rail && (
            <span className="min-w-0 text-[13px] leading-tight">
              <span className="block truncate font-medium text-zinc-800">Local workspace</span>
              <span className="block truncate text-zinc-500">{health?.site ?? 'CartMind'}</span>
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
