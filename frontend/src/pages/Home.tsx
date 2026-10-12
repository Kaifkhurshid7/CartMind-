import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Composer from '../components/Chat/Composer'
import { STARTER_PROMPTS } from '../components/Chat/PromptLibrary'
import { HeadphonesIcon, LaptopIcon, LogoMark, PhoneIcon } from '../components/icons'
import Shell from '../components/Shell/Shell'
import SuggestionCard from '../components/ui/SuggestionCard'
import { errorMessage } from '../services/api'
import { startShopping } from '../services/shopping'

const SUGGESTIONS = [
  { icon: <LaptopIcon width={18} height={18} />, title: 'Laptop for coding', meta: 'Under ₹50,000 · 16GB RAM · 512GB SSD', prompt: STARTER_PROMPTS[0] },
  { icon: <HeadphonesIcon width={18} height={18} />, title: 'Wireless headphones', meta: 'Under ₹3,000 · ANC · long battery', prompt: STARTER_PROMPTS[1] },
  { icon: <PhoneIcon width={18} height={18} />, title: 'Camera smartphone', meta: 'Under ₹25,000 · 8GB RAM', prompt: STARTER_PROMPTS[2] },
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
              <LogoMark size={36} />
            </div>
            <h1 className="text-[28px] font-semibold leading-9 tracking-tight text-fg sm:text-[32px] sm:leading-10">What are you looking for?</h1>
            <p className="mx-auto mt-3 max-w-[560px] text-[15px] leading-6 text-fg-2">
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

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            {SUGGESTIONS.map((c) => (
              <SuggestionCard key={c.title} icon={c.icon} title={c.title} meta={c.meta} prompt={c.prompt} onPick={setQuery} />
            ))}
          </div>
        </div>
      </div>
      <p className="shrink-0 px-4 pb-3 text-center text-[12px] text-fg-3">
        CartMind asks for your approval before acting and always stops before payment.
      </p>
    </Shell>
  )
}
