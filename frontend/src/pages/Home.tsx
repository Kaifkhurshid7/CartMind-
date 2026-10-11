import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Composer from '../components/Chat/Composer'
import { Avatar } from '../components/icons'
import Shell from '../components/Shell/Shell'
import { useHealth } from '../hooks/useHealth'
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
  const health = useHealth()

  async function submit() {
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
    <Shell>
      <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-10">
        <div className="w-full max-w-[640px]">
          <div className="mb-8 text-center">
            <div className="mb-4 flex justify-center">
              <Avatar size={44} />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">What are you looking for?</h1>
            <p className="mt-2 text-[15px] text-zinc-500">Tell CartMind what you want. It finds the best option and shops for you.</p>
          </div>

          <Composer
            value={query}
            onChange={setQuery}
            onSubmit={submit}
            health={health}
            sending={loading}
            autoFocus
            placeholder="I need a laptop under ₹50,000 for coding"
          />
          {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

          <div className="mt-5 flex flex-col items-stretch gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                className="rounded-xl border border-zinc-200 px-4 py-2.5 text-left text-sm text-zinc-600 transition hover:bg-zinc-50"
                onClick={() => setQuery(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>
      <p className="pb-3 text-center text-[11px] text-zinc-400">
        CartMind asks for your approval before acting and always stops before payment.
      </p>
    </Shell>
  )
}
