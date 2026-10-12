import type { ReactNode } from 'react'

/** Shared row styling for sidebar navigation, settings and similar full-width items. */
export const navRowCls = (active: boolean) =>
  `flex h-9 w-full items-center gap-3 overflow-hidden whitespace-nowrap rounded-control px-3 text-[14px] transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
    active ? 'bg-active-nav font-medium text-fg' : 'text-fg-2 hover:bg-hover-nav hover:text-fg'
  }`

/** Label that fades with the collapsing sidebar instead of wrapping. */
export function NavLabel({ hidden, children }: { hidden: boolean; children: ReactNode }) {
  return <span className={`min-w-0 truncate transition-opacity duration-fast ${hidden ? 'opacity-0' : 'opacity-100'}`}>{children}</span>
}
