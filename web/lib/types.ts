export type Citation = {
  doc_id?: string
  chunk_id?: string
  title?: string
  source?: string
  page?: number | null
  score?: number | null
  snippet?: string
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: Citation[]
  thinking?: boolean
}

export type Conversation = {
  id: string
  title: string
  createdAt: number
  messages: ChatMessage[]
}
