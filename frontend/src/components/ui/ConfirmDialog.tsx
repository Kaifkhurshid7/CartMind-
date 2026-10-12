import { useEffect } from 'react'

interface Props {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}

/** Small modal for destructive confirmations. Escape and backdrop click cancel. */
export default function ConfirmDialog({ open, title, description, confirmLabel, onConfirm, onCancel }: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onCancel])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 animate-fade-in bg-zinc-900/30" onClick={onCancel} aria-hidden="true" />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="relative w-full max-w-sm animate-fade-up rounded-card border border-line bg-white p-6 shadow-lg"
      >
        <h2 id="confirm-title" className="text-[16px] font-semibold text-fg">
          {title}
        </h2>
        <p className="mt-2 break-words text-[14px] leading-6 text-fg-2">{description}</p>
        <div className="mt-6 flex justify-end gap-2">
          <button className="btn-ghost" onClick={onCancel} autoFocus>
            Cancel
          </button>
          <button className="btn bg-rose-600 text-white hover:bg-rose-700" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
