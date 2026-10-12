import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom'
import type { Health } from '../../hooks/useHealth'
import { groupByDate, hideSession, renameSession, useSessionPrefs } from '../../services/sessionPrefs'
import { listSessions } from '../../services/shopping'
import type { SessionSummary } from '../../types/shopping'
import { ClockIcon, GearIcon, HomeIcon, LogoMark, SearchIcon, SidebarIcon } from '../icons'
import { NavLabel, navRowCls } from '../ui/NavRow'
import Popover from '../ui/Popover'
import HistoryItem from './HistoryItem'

const USER_NAME = 'Kaif Khurshid'

interface Props {
  health: Health | null
  /** Icon-only rail (desktop). */
  rail: boolean
  onToggleRail: () => void
  /** Closes the mobile drawer after navigating. */
  onNavigate: () => void
}

function modelLabel(h: Health): string {
  if (!h.llm_configured || !h.llm_model) return 'Basic matching'
  const m = h.llm_model.replace(/[-_]/g, ' ')
  return m.charAt(0).toUpperCase() + m.slice(1)
}

function storesLabel(site: string): string {
  return site.replace(/^web:\s*/i, '')
}

function SectionLabel({ children }: { children: string }) {
  return <p className="animate-fade-in px-3 pb-1 pt-4 text-[12px] font-medium uppercase tracking-wider text-fg-3">{children}</p>
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-start justify-between gap-4 text-[13px]">
      <span className="text-fg-3">{k}</span>
      <span className="min-w-0 text-right font-medium text-fg">{v}</span>
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

  return (
    <div className="flex h-full min-h-0 flex-col bg-sidebar px-4 py-4">
      {/* Brand: logo, wordmark, collapse. In the rail the expand button takes its place. */}
      <div className="flex h-10 shrink-0 items-center justify-between">
        {rail ? (
          <button className={navRowCls(false)} aria-label="Expand sidebar" title="Expand sidebar" onClick={onToggleRail}>
            <SidebarIcon width={18} height={18} className="shrink-0" />
          </button>
        ) : (
          <>
            <Link to="/" onClick={onNavigate} className="flex items-center gap-2.5 rounded-control px-1 text-[18px] font-semibold tracking-tight text-fg focus-ring">
              <LogoMark size={24} />
              CartMind
            </Link>
            <button className="icon-btn hidden !h-8 !w-8 md:inline-flex" aria-label="Collapse sidebar" title="Collapse sidebar" onClick={onToggleRail}>
              <SidebarIcon width={18} height={18} />
            </button>
          </>
        )}
      </div>

      {/* Workspace */}
      {!rail && <SectionLabel>Workspace</SectionLabel>}
      <nav className={`flex flex-col gap-0.5 ${rail ? 'mt-4' : ''}`} aria-label="Workspace">
        <NavLink to="/" end onClick={onNavigate} title="Home" aria-label="Home" className={({ isActive }) => navRowCls(isActive)}>
          <HomeIcon width={18} height={18} className="shrink-0" />
          <NavLabel hidden={rail}>Home</NavLabel>
        </NavLink>
        <NavLink to="/history" onClick={onNavigate} title="All searches" aria-label="All searches" className={({ isActive }) => navRowCls(isActive)}>
          <ClockIcon width={18} height={18} className="shrink-0" />
          <NavLabel hidden={rail}>All searches</NavLabel>
        </NavLink>
      </nav>

      {/* History: the only scrolling region */}
      {!rail ? (
        <div className="flex min-h-0 flex-1 animate-fade-in flex-col">
          <SectionLabel>History</SectionLabel>
          <label className="mb-2 flex h-9 shrink-0 items-center gap-2 rounded-control border border-line bg-white px-3 text-fg-3 transition-colors duration-fast focus-within:border-line-strong focus-within:ring-2 focus-within:ring-primary/10">
            <SearchIcon width={15} height={15} className="shrink-0" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations"
              aria-label="Search conversations"
              className="min-w-0 flex-1 bg-transparent text-[14px] text-fg outline-none placeholder:text-placeholder"
            />
          </label>
          <div className="-mr-2 min-h-0 flex-1 overflow-y-auto overscroll-contain pr-2">
            {groups.length === 0 && (
              <p className="px-3 py-2 text-[13px] text-fg-3">
                {hasAny ? 'No conversations match your search.' : 'No conversations yet. Start a new session.'}
              </p>
            )}
            {groups.map((g) => (
              <section key={g.label} className="mb-2">
                <h3 className="px-3 pb-1 pt-2 text-[12px] font-medium text-fg-3">{g.label}</h3>
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
      <div className="relative mt-2 shrink-0 space-y-1 border-t border-line-sidebar pt-3">
        <Popover open={settingsOpen} onClose={closeSettings} className={`bottom-full mb-2 ${rail ? 'left-0 w-64' : 'inset-x-0'}`}>
          <div className="rounded-card border border-line bg-white p-4 shadow-lg">
            <p className="text-[14px] font-semibold text-fg">{USER_NAME}</p>
            <p className="pb-2 text-[13px] text-fg-3">Shopping workspace</p>
            <div className="space-y-2.5 border-t border-line pt-3">
              <Row k="Assistant" v={health ? modelLabel(health) : '…'} />
              <Row k="Mode" v={health ? (health.shopping_mode === 'live' ? 'Live shopping' : 'Demo catalog') : '…'} />
              <Row k="Stores" v={health ? storesLabel(health.site) : '…'} />
            </div>
            <p className="mt-3 border-t border-line pt-3 text-[12px] leading-relaxed text-fg-3">
              CartMind asks before every action and never completes payment.
            </p>
          </div>
        </Popover>
        <button
          onClick={() => setSettingsOpen((o) => !o)}
          aria-haspopup="dialog"
          aria-expanded={settingsOpen}
          aria-label="Settings"
          title="Settings"
          className={navRowCls(settingsOpen)}
        >
          <GearIcon width={18} height={18} className="shrink-0" />
          <NavLabel hidden={rail}>Settings</NavLabel>
        </button>
        <div className="flex h-11 items-center gap-3 overflow-hidden px-1.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-active-nav text-[13px] font-semibold text-fg-2" aria-hidden="true">
            {USER_NAME.charAt(0)}
          </span>
          <span className={`min-w-0 text-[13px] leading-tight transition-opacity duration-fast ${rail ? 'opacity-0' : 'opacity-100'}`}>
            <span className="block truncate font-medium text-fg">{USER_NAME}</span>
            <span className="block truncate text-fg-3">{health?.site ?? 'CartMind'}</span>
          </span>
        </div>
      </div>
    </div>
  )
}
