export interface Product {
  id: string
  name: string
  brand: string
  category: string
  price: number
  currency: string
  specs: Record<string, string | number | boolean>
  rating: number
  review_count: number
  available: boolean
  url: string
  source: string
  features: string[]
  suitability?: number
  score_breakdown?: Record<string, number>
}
