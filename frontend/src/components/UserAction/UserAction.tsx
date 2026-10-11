interface Props {
  message: string
  busy: boolean
  onContinue: () => void
  onCancel: () => void
}

/** The agent has paused: something in the browser window needs a human (sign in, robot check). */
export default function UserAction({ message, busy, onContinue, onCancel }: Props) {
  return (
    <section
      className="rounded-xl border border-amber-300 bg-amber-50/70 p-4"
      role="region"
      aria-label="Action needed"
      data-testid="user-action"
    >
      <p className="text-[11px] font-medium uppercase tracking-wider text-amber-700">Action needed in the browser window</p>
      <p className="mt-1 text-sm text-zinc-800">{message}</p>
      <p className="mt-2 text-xs text-zinc-500">
        Do this yourself in the Chrome window CartMind opened. CartMind never types passwords or solves robot checks.
      </p>
      <div className="mt-3 flex gap-2">
        <button className="btn-primary" onClick={onContinue} disabled={busy}>
          I&apos;m done, continue
        </button>
        <button className="btn-ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </section>
  )
}
