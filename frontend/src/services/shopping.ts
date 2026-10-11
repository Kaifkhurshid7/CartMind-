import { api } from './api'
import type { ChatReply, SessionSummary, ShoppingSession } from '../types/shopping'

export const startShopping = (query: string) =>
  api.post<{ session_id: string }>('/api/shopping/start', { query }).then((r) => r.data.session_id)

export const getSession = (id: string) => api.get<ShoppingSession>(`/api/shopping/${id}`).then((r) => r.data)

export const listSessions = () => api.get<SessionSummary[]>('/api/shopping/sessions').then((r) => r.data)

export const approve = (id: string, productId: string | null, acceptPriceChange = false) =>
  api
    .post(`/api/shopping/${id}/approve`, { approved: true, product_id: productId, accept_price_change: acceptPriceChange })
    .then((r) => r.data)

export const cancelSession = (id: string) => api.post(`/api/shopping/${id}/cancel`).then((r) => r.data)

export const sendChat = (id: string, message: string) =>
  api.post<ChatReply>(`/api/chat/${id}`, { message }).then((r) => r.data)

export const inr = (n: number | null | undefined) =>
  n == null ? '—' : `₹${Math.round(n).toLocaleString('en-IN')}`
