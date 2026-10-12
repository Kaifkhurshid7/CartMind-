import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Composer from '../components/Chat/Composer'
import { STARTER_PROMPTS } from '../components/Chat/PromptLibrary'
import { LogoMark } from '../components/icons'
import Shell from '../components/Shell/Shell'
import { errorMessage } from '../services/api'
import { startShopping } from '../services/shopping'

export default function Home() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

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
        <div className="w-full max-w-[720px]">
          <div className="mb-8 text-center">
            <div className="mb-4 flex justify-center">
              <LogoMark size={44} />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">What would you like to buy?</h1>
            <p className="mt-2 text-[15px] text-zinc-500">
              Describe it in plain language. CartMind researches the options and adds your pick to the cart after you approve.
            </p>
          </div>

          <Composer
            value={query}
            onChange={setQuery}
            onSubmit={() => void submit()}
            prompts={STARTER_PROMPTS}
            sending={loading}
            autoFocus
            placeholder="Ask me anything"
          />
          {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {STARTER_PROMPTS.slice(0, 3).map((p) => (
              <button
                key={p}
                onClick={() => setQuery(p)}
                className="max-w-[280px] truncate rounded-xl bg-zinc-100 px-3 py-1.5 text-[13px] text-zinc-600 transition hover:bg-zinc-200"
                title={p}
              >
                {p}
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
