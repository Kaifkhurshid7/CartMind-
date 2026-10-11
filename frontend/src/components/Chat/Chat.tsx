import { FormEvent, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../../services/api'
import { sendChat } from '../../services/shopping'
import type { ChatMessage } from '../../types/shopping'

const SUGGESTIONS = ['Why did you choose this?', 'Which one has better battery life?', 'What if I increase my budget to ₹60k?']

interface Props {
  sessionId: string
  messages: ChatMessage[]
  disabled?: boolean
  onAction: (action: string | null) => void
}

export default function Chat({ sessionId, messages, disabled, onAction }: Props) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => endRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), [messages.length, sending])

  async function submit(message: string) {
    if (!message.trim() || sending) return
    setSending(true)
    setErr(null)
    setText('')
    try {
      const res = await sendChat(sessionId, message.trim())
      onAction(res.action)
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setSending(false)
    }
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    void submit(text)
  }

  return (
    <section className="card flex flex-col" aria-label="Chat">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Ask CartMind</h2>
      <div className="mb-3 max-h-80 min-h-[8rem] space-y-2 overflow-y-auto pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <p
              className={`max-w-[88%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
                m.role === 'user' ? 'bg-brand-500 text-white' : 'bg-white/10 text-slate-200'
              }`}
            >
              {m.content}
            </p>
          </div>
        ))}
        {sending && <p className="animate-pulse text-xs text-slate-500">CartMind is thinking…</p>}
        <div ref={endRef} />
      </div>

      {!disabled && messages.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="chip hover:bg-white/20" onClick={() => void submit(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      {err && <p className="mb-2 text-xs text-rose-400">{err}</p>}
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask a question or change your requirements…"
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-ink-800 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-brand-500"
          disabled={disabled}
        />
        <button className="btn-primary" disabled={disabled || sending || !text.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
