import { ReactNode, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useHealth } from '../../hooks/useHealth'
import { ChevronDown, LinkIcon, SidebarIcon, SlidersIcon, XIcon } from '../icons'
import Popover from '../ui/Popover'
import Sidebar from '../Sidebar/Sidebar'

export interface ControlProps {
  busy?: boolean
  onCancel?: () => void
}

const KEY = 'cartmind:sidebar-collapsed'

function loadCollapsed(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

/** App frame: sidebar, top bar (model details + controls), content, and an optional pinned footer. */
export default function Shell({ children, footer, control }: { children: ReactNode; footer?: ReactNode; control?: ControlProps }) {
  const health = useHealth()
  const [collapsed, setCollapsed] = useState(loadCollapsed)
  const [modelOpen, setModelOpen] = useState(false)
  const [controlOpen, setControlOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(KEY, collapsed ? '1' : '0')
    } catch {
      /* storage unavailable */
    }
  }, [collapsed])

  const closeModel = useCallback(() => setModelOpen(false), [])
  const closeControl = useCallback(() => setControlOpen(false), [])

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    } catch {
      /* clipboard unavailable */
    }
  }

  const modelLabel = health ? (health.llm_model ?? 'Rule-based') : '…'

  return (
    <div className="h-full p-2 sm:p-2.5">
      <div className="flex h-full overflow-hidden rounded-2xl border border-zinc-200/80 bg-[#fcfcfb] shadow-sm">
        {!collapsed && <Sidebar health={health} onCollapse={() => setCollapsed(true)} />}

        <div className="surface flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 shrink-0 items-center justify-between px-4 sm:px-6">
            <div className="relative flex items-center gap-2">
              {collapsed && (
                <button className="icon-btn" aria-label="Open sidebar" onClick={() => setCollapsed(false)}>
                  <SidebarIcon />
                </button>
              )}
              <button
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium text-zinc-800 hover:bg-zinc-100"
                onClick={() => setModelOpen((o) => !o)}
                aria-haspopup="dialog"
                aria-expanded={modelOpen}
              >
                <span className="h-3.5 w-3.5 rounded-full bg-gradient-to-br from-orange-300 to-orange-500" />
                {modelLabel}
                <ChevronDown width={14} height={14} className="text-zinc-400" />
              </button>
              <Popover open={modelOpen} onClose={closeModel} className="left-0 top-full mt-1 w-64">
                <div className="rounded-xl border border-zinc-200 bg-white p-3 shadow-lg">
                  <div className="flex justify-between py-1 text-[13px]"><span className="text-zinc-500">Mode</span><span className="font-medium">{health?.shopping_mode ?? '…'}</span></div>
                  <div className="flex justify-between py-1 text-[13px]"><span className="text-zinc-500">Model</span><span className="font-medium">{health?.llm_model ?? 'none'}</span></div>
                  <div className="flex justify-between py-1 text-[13px]"><span className="text-zinc-500">Shop</span><span className="font-medium">{health?.site ?? '…'}</span></div>
                  {health && !health.llm_configured && (
                    <p className="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-800">
                      No AI key found. Add GEMINI_API_KEY_1 to .env and restart the backend.
                    </p>
                  )}
                </div>
              </Popover>
            </div>

            <div className="relative">
              <button
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100"
                onClick={() => setControlOpen((o) => !o)}
                aria-haspopup="dialog"
                aria-expanded={controlOpen}
              >
                <SlidersIcon width={15} height={15} />
                Control
              </button>
              <Popover open={controlOpen} onClose={closeControl} className="right-0 top-full mt-1 w-60">
                <div className="rounded-xl border border-zinc-200 bg-white p-1.5 shadow-lg">
                  <button
                    disabled={!control?.busy}
                    onClick={() => {
                      control?.onCancel?.()
                      setControlOpen(false)
                    }}
                    className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[14px] text-zinc-800 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:text-zinc-300 disabled:hover:bg-transparent"
                  >
                    <XIcon width={15} height={15} />
                    Stop current task
                  </button>
                  <button onClick={copyLink} className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[14px] text-zinc-800 hover:bg-zinc-50">
                    <LinkIcon width={15} height={15} />
                    {copied ? 'Link copied' : 'Copy link to this chat'}
                  </button>
                  <Link to="/history" onClick={() => setControlOpen(false)} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-[14px] text-zinc-800 hover:bg-zinc-50">
                    All searches
                  </Link>
                </div>
              </Popover>
            </div>
          </header>

          <div className="flex min-h-0 flex-1 flex-col">{children}</div>
          {footer}
        </div>
      </div>
    </div>
  )
}
