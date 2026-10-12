import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Composer from '../components/Chat/Composer'
import { STARTER_PROMPTS } from '../components/Chat/PromptLibrary'
import { BagIcon, ChatIcon, LogoMark, SparkIcon } from '../components/icons'
import Shell from '../components/Shell/Shell'
import SuggestionCard from '../components/ui/SuggestionCard'
import { errorMessage } from '../services/api'
import { startShopping } from '../services/shopping'

const SUGGESTION_ICONS = [
  <ChatIcon key="a" width={16} height={16} />,
  <SparkIcon key="b" width={16} height={16} />,
  <BagIcon key="c" width={16} height={16} />,
]

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
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-4 py-8 md:px-6">
        <div className="w-full max-w-[760px]">
          <div className="mb-6 text-center">
            <div className="mb-4 flex justify-center">
              <LogoMark size={40} />
            </div>
            <h1 className="text-[28px] font-semibold leading-9 tracking-tight text-zinc-900 sm:text-[32px] sm:leading-10">What are you looking for?</h1>
            <p className="mx-auto mt-3 max-w-[560px] text-[15px] leading-6 text-zinc-600">
              Tell CartMind what you need. I&apos;ll research products, compare options, and help you find the right fit.
            </p>
          </div>

          <Composer
            value={query}
            onChange={setQuery}
            onSubmit={() => void submit()}
            prompts={STARTER_PROMPTS}
            sending={loading}
            autoFocus
            placeholder="Tell CartMind what you're looking to buy..."
          />
          {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

          <div className="mt-6 space-y-2">
            {STARTER_PROMPTS.slice(0, 3).map((p, i) => (
              <SuggestionCard key={p} text={p} onPick={setQuery} icon={SUGGESTION_ICONS[i]} />
            ))}
          </div>
        </div>
      </div>
      <p className="shrink-0 px-4 pb-3 text-center text-[12px] text-zinc-500">
        CartMind asks for your approval before acting and always stops before payment.
      </p>
    </Shell>
  )
}
