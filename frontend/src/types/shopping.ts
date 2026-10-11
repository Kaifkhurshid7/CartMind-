import type { Product } from './product'

export type SessionStatus =
  | 'started'
  | 'running'
  | 'waiting_for_approval'
  | 'executing'
  | 'price_changed'
  | 'completed'
  | 'cancelled'
  | 'failed'
  | 'no_results'
  | 'needs_clarification'

export interface Requirements {
  category: string
  budget: { maximum: number | null; currency: string }
  use_case: string | null
  requirements: Record<string, string>
  preferences: string[]
  priorities: string[]
  location: string
}

export interface Recommendation {
  product: Product
  alternatives: Product[]
  summary: string
  reasons: string[]
  disadvantages: string[]
  alternative_note: string
}

export interface ComparisonRow {
  id: string
  name: string
  price: number
  specs: Record<string, string | number | boolean>
  rating: number
  review_count: number
  suitability: number
}

export interface Comparison {
  table?: ComparisonRow[]
  summary?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface CartState {
  items?: { product_id: string; name: string; price: number }[]
  total?: number
  url?: string
}

export interface NearMiss {
  product: Product
  fails: string
}

export interface ShoppingSession {
  id: string
  query: string
  status: SessionStatus
  current_step: string
  requirements: Partial<Requirements>
  search_count: number
  shortlisted_products: Product[]
  comparison: Comparison
  review_analysis: Record<string, string>
  recommendation: Partial<Recommendation>
  cart_state: CartState
  browser_state: Record<string, unknown>
  near_misses: NearMiss[]
  messages: ChatMessage[]
  price_change?: { old: number; new: number }
  error: string | null
  created_at: string | null
  updated_at: string | null
}

export interface SessionSummary {
  id: string
  query: string
  status: SessionStatus
  current_step: string
  product_name: string | null
  price: number | null
  created_at: string | null
}

export interface ChatReply {
  reply: string
  intent: string
  action: string | null
}
