import { ReactNode, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Avatar, ChevronDown, LinkIcon, XIcon } from '../icons'

/** Outer frame: grey margin, white rounded panel, top bar (close · agent name · link · actions). */
export default function Shell({ children, footer }: { children: ReactNode; footer?: ReactNode }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [menu, setMenu] = useState(false)
  const [copied, setCopied] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const home = pathname === '/'

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard unavailable (insecure context) — ignore */
    }
  }

  return (
    <div className="flex h-full flex-col p-2 sm:p-2.5">
      <div className="mx-auto flex min-h-0 w-full flex-1 flex-col overflow-hidden rounded-2xl border border-zinc-200/80 bg-white shadow-sm">
        <header className="flex h-[50px] shrink-0 items-center justify-between border-b border-zinc-200 px-3 sm:px-4">
          <div className="flex items-center gap-2">
            {!home && (
              <button className="icon-btn" aria-label="Close" onClick={() => navigate('/')}>
                <XIcon />
              </button>
            )}
            <div className="relative" ref={menuRef}>
              <button
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium hover:bg-zinc-50"
                onClick={() => setMenu((m) => !m)}
                aria-haspopup="menu"
              >
                <Avatar />
                CartMind
                <ChevronDown className="text-zinc-400" />
              </button>
              {menu && (
                <div role="menu" className="absolute left-0 top-full z-20 mt-1 w-44 rounded-xl border border-zinc-200 bg-white p-1 shadow-lg">
                  <Link role="menuitem" to="/" onClick={() => setMenu(false)} className="block rounded-lg px-3 py-2 text-sm hover:bg-zinc-50">
                    New search
                  </Link>
                  <Link role="menuitem" to="/history" onClick={() => setMenu(false)} className="block rounded-lg px-3 py-2 text-sm hover:bg-zinc-50">
                    History
                  </Link>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="icon-btn" aria-label="Copy link" title={copied ? 'Copied!' : 'Copy link'} onClick={copyLink}>
              <LinkIcon />
            </button>
            <Link to="/history" className="btn-ghost !py-1.5">
              History
            </Link>
            <Link to="/" className="btn-soft !py-1.5">
              New search
            </Link>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        {footer}
      </div>
    </div>
  )
}
