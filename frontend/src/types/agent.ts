export type EventStatus = 'done' | 'running' | 'waiting' | 'error'

export interface AgentEvent {
  id: number
  session_id: string
  step: string
  message: string
  status: EventStatus
  timestamp: string
}
