import { useCallback, useState } from 'react'
import { MoreIcon, PencilIcon, TrashIcon } from '../icons'
import Popover from '../ui/Popover'

interface Props {
  title: string
  onOpen: () => void
  onRename: () => void
  onDelete: () => void
}

const item =
  'flex h-9 w-full items-center gap-2.5 rounded-lg px-3 text-left text-[14px] transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30'

// Hidden until hover on devices that have hover; always visible on touch.
const HOVER_ONLY =
  '[@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-focus-within:opacity-100 [@media(hover:hover)]:group-hover:opacity-100'

/** Three-dot menu for a history card. Sits above the card's stretched link. */
export default function HistoryActionsMenu({ title, onOpen, onRename, onDelete }: Props) {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const run = (fn: () => void) => () => {
    setOpen(false)
    fn()
  }

  return (
    <div className="relative z-10">
      <button
        className={`icon-btn !h-8 !w-8 ${open ? '' : HOVER_ONLY}`}
        aria-label={`Actions for ${title}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <MoreIcon width={16} height={16} />
      </button>
      <Popover open={open} onClose={close} className="right-0 top-full mt-1 w-52">
        <div role="menu" className="animate-fade-in rounded-control border border-line bg-white p-1 shadow-lg">
          <button role="menuitem" className={`${item} text-fg hover:bg-hover`} onClick={run(onOpen)}>
            Open conversation
          </button>
          <button role="menuitem" className={`${item} text-fg hover:bg-hover`} onClick={run(onRename)}>
            <PencilIcon width={14} height={14} />
            Rename
          </button>
          <button role="menuitem" className={`${item} text-rose-700 hover:bg-rose-50`} onClick={run(onDelete)}>
            <TrashIcon width={14} height={14} />
            Delete conversation
          </button>
        </div>
      </Popover>
    </div>
  )
}
