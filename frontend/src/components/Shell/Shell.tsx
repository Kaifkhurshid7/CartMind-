import { ReactNode, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useHealth } from '../../hooks/useHealth'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import { LinkIcon, MenuIcon, SlidersIcon, XIcon } from '../icons'
import Popover from '../ui/Popover'
import Sidebar from '../Sidebar/Sidebar'

export interface ControlProps {
  busy?: boolean
  onCancel?: () => void
}

interface Props {
  children: ReactNode
  footer?: ReactNode
  control?: ControlProps
  /** Conversation title for the top bar. */
  title?: string
}

const KEY = 'cartmind:sidebar-collapsed'

function loadCollapsed(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

/** App frame: sidebar (rail on desktop, drawer on mobile), compact top bar, content, optional footer. */
export default function Shell({ children, footer, control, title }: Props) {
  const health = useHealth()
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const [collapsed, setCollapsed] = useState(loadCollapsed)
  const [drawer, setDrawer] = useState(false)
  const [controlOpen, setControlOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, collapsed ? '1' : '0')
    } catch {
      /* storage unavailable */
    }
  }, [collapsed])

  useEffect(() => {
    if (isDesktop) setDrawer(false)
  }, [isDesktop])

  const closeControl = useCallback(() => setControlOpen(false), [])
  const rail = isDesktop && collapsed

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-app text-fg">
      {drawer && <div className="fixed inset-0 z-30 bg-zinc-900/30 md:hidden" onClick={() => setDrawer(false)} aria-hidden="true" />}

      <aside
        aria-label="Sidebar"
        className={`fixed inset-y-0 left-0 z-40 h-full w-[280px] max-w-[85vw] -translate-x-full overflow-hidden border-r border-line-sidebar bg-sidebar transition-transform duration-200 md:static md:z-auto md:max-w-none md:flex-none md:translate-x-0 md:transition-[width] md:duration-200 ${
          drawer ? 'translate-x-0' : ''
        } ${collapsed ? 'md:w-[72px]' : 'md:w-[280px]'}`}
      >
        <Sidebar health={health} rail={rail} onToggleRail={() => setCollapsed((c) => !c)} onNavigate={() => setDrawer(false)} />
      </aside>

      <main className="flex h-full min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-line px-4 md:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <button className="icon-btn !h-9 !w-9 md:hidden" aria-label="Open sidebar" title="Open sidebar" onClick={() => setDrawer(true)}>
              <MenuIcon width={18} height={18} />
            </button>
            {title ? (
              <>
                <h1 className="min-w-0 truncate text-[14px] font-medium text-fg" title={title}>
                  {title}
                </h1>
              </>
            ) : (
              <span className="text-[14px] font-medium text-fg">CartMind</span>
            )}
          </div>

          {control && (
            <div className="relative shrink-0">
              <button
                className="flex h-9 items-center gap-2 rounded-lg px-2.5 text-[14px] text-zinc-600 transition hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900/30"
                onClick={() => setControlOpen((o) => !o)}
                aria-haspopup="dialog"
                aria-expanded={controlOpen}
                aria-label="Session controls"
              >
                <SlidersIcon width={15} height={15} />
                <span className="hidden sm:inline">Control</span>
              </button>
              <Popover open={controlOpen} onClose={closeControl} className="right-0 top-full mt-1 w-60">
                <div className="rounded-xl border border-zinc-200 bg-white p-1.5 shadow-lg">
                  <button
                    disabled={!control.busy}
                    onClick={() => {
                      control.onCancel?.()
                      setControlOpen(false)
                    }}
                    className="flex h-10 w-full items-center gap-2.5 rounded-lg px-3 text-left text-[14px] text-zinc-800 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-300 disabled:hover:bg-transparent"
                  >
                    <XIcon width={15} height={15} />
                    Stop current task
                  </button>
                  <button onClick={copyLink} className="flex h-10 w-full items-center gap-2.5 rounded-lg px-3 text-left text-[14px] text-zinc-800 hover:bg-zinc-50">
                    <LinkIcon width={15} height={15} />
                    {copied ? 'Link copied' : 'Copy link to this chat'}
                  </button>
                  <Link to="/history" onClick={closeControl} className="flex h-10 items-center gap-2.5 rounded-lg px-3 text-[14px] text-zinc-800 hover:bg-zinc-50">
                    All searches
                  </Link>
                </div>
              </Popover>
            </div>
          )}
        </header>

        <div className="flex min-h-0 flex-1 animate-fade-in flex-col">{children}</div>
        {footer}
      </main>
    </div>
  )
}
