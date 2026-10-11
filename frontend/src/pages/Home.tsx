import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { errorMessage } from '../services/api'
import { startShopping } from '../services/shopping'

const EXAMPLES = [
  'I need a laptop under ₹50,000 for coding with at least 16GB RAM and 512GB SSD',
  'Wireless headphones under ₹5,000 with ANC and at least 30 hours battery life',
  'Find me a phone under ₹25,000 with a great camera and 8GB RAM',
]

export default function Home() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function submit(e?: FormEvent) {
    e?.preventDefault()
    if (query.trim().length < 3 || loading) return
    setLoading(true)
    setError(null)
    try {
      navigate(`/session/${await startShopping(query.trim())}`)
    } catch (err) {
      setError(errorMessage(err))
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center text-center">
      <h1 className="bg-gradient-to-r from-white to-brand-400 bg-clip-text text-5xl font-extrabold tracking-tight text-transparent sm:text-6xl">
        CartMind
      </h1>
      <p className="mt-3 text-lg text-slate-300">Tell CartMind what you want. It finds the best option and shops for you.</p>

      <form onSubmit={submit} className="card mt-10 w-full space-y-4 text-left">
        <label htmlFor="query" className="text-sm font-medium text-slate-300">
          What are you looking for?
        </label>
        <textarea
          id="query"
          rows={3}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) void submit(e)
          }}
          placeholder="I need a laptop under ₹50,000 for coding"
          className="w-full resize-none rounded-xl border border-white/10 bg-ink-800 p-3 text-white outline-none placeholder:text-slate-500 focus:border-brand-500"
        />
        {error && <p className="text-sm text-rose-400">{error}</p>}
        <button className="btn-primary w-full py-3 text-base" disabled={loading || query.trim().length < 3}>
          {loading ? 'Starting…' : 'Start Shopping'}
        </button>
      </form>

      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} className="chip max-w-xs truncate hover:bg-white/20" title={ex} onClick={() => setQuery(ex)}>
            {ex}
          </button>
        ))}
      </div>

      <p className="mt-10 text-xs text-slate-500">
        CartMind always asks for your approval before acting and stops before payment.
      </p>
    </div>
  )
}
