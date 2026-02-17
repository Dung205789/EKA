'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { Message } from '@/components/Message'
import type { ChatMessage, Conversation, Citation } from '@/lib/types'
import { parseSSE } from '@/lib/sse'

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16)
}

const LS_KEY = 'eka.conversations.v1'
const LS_ACTIVE = 'eka.activeConversationId'

function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return []
    return JSON.parse(raw)
  } catch {
    return []
  }
}

function saveConversations(convs: Conversation[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(convs))
}

export function ChatClient() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const convs = loadConversations()
    setConversations(convs)
    const savedActive = localStorage.getItem(LS_ACTIVE)
    if (savedActive && convs.some((c) => c.id === savedActive)) {
      setActiveId(savedActive)
    } else {
      setActiveId(convs[0]?.id ?? null)
    }
  }, [])

  useEffect(() => {
    saveConversations(conversations)
  }, [conversations])

  useEffect(() => {
    if (activeId) localStorage.setItem(LS_ACTIVE, activeId)
  }, [activeId])

  const activeConversation = useMemo(() => {
    return conversations.find((c) => c.id === activeId) ?? null
  }, [conversations, activeId])

  function createNewConversation() {
    const c: Conversation = {
      id: uid(),
      title: 'New chat',
      createdAt: Date.now(),
      messages: [
        {
          id: uid(),
          role: 'system',
          content:
            'EKA Brain is running local-first. Upload documents under Documents, then ask questions here.'
        }
      ]
    }
    const next = [c, ...conversations]
    setConversations(next)
    setActiveId(c.id)
  }

  function updateConversation(id: string, updater: (c: Conversation) => Conversation) {
    setConversations((prev) => prev.map((c) => (c.id === id ? updater(c) : c)))
  }

  async function sendMessage() {
    if (!activeId || isStreaming) return
    const q = input.trim()
    if (!q) return

    setInput('')
    const userMsg: ChatMessage = { id: uid(), role: 'user', content: q }
    const assistantMsg: ChatMessage = { id: uid(), role: 'assistant', content: '', thinking: true }

    updateConversation(activeId, (c) => {
      const title = c.title === 'New chat' ? q.slice(0, 48) : c.title
      return { ...c, title, messages: [...c.messages, userMsg, assistantMsg] }
    })

    setIsStreaming(true)

    try {
      const resp = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      })

      if (!resp.ok || !resp.body) {
        const errText = await resp.text()
        throw new Error(errText || `HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let citations: Citation[] | undefined

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const parsed = parseSSE(buffer)
        buffer = parsed.rest

        for (const evt of parsed.events) {
          if (evt.event === 'meta') {
            try {
              const meta = JSON.parse(evt.data)
              citations = meta.citations
            } catch {
              // ignore
            }
          }
          if (evt.event === 'token') {
            try {
              const obj = JSON.parse(evt.data)
              const delta = obj.delta as string
              if (delta) {
                updateConversation(activeId, (c) => {
                  const msgs = c.messages.map((m) =>
                    m.id === assistantMsg.id
                      ? { ...m, thinking: false, content: m.content + delta }
                      : m
                  )
                  return { ...c, messages: msgs }
                })
              }
            } catch {
              // ignore
            }
          }
          if (evt.event === 'error') {
            updateConversation(activeId, (c) => {
              const msgs = c.messages.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, thinking: false, content: m.content + `\n\n[Error]\n${evt.data}` }
                  : m
              )
              return { ...c, messages: msgs }
            })
          }
          if (evt.event === 'done') {
            // finalize message + attach citations (if any)
            updateConversation(activeId, (c) => {
              const msgs = c.messages.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      thinking: false,
                      citations: citations && citations.length > 0 ? citations : m.citations
                    }
                  : m
              )
              return { ...c, messages: msgs }
            })
          }
        }
      }
    } catch (e: any) {
      updateConversation(activeId, (c) => {
        const msgs = c.messages.map((m) =>
          m.id === assistantMsg.id
            ? {
                ...m,
                thinking: false,
                content:
                  'Sorry — the request failed.\n\n' +
                  (e?.message || String(e) || 'Unknown error')
              }
            : m
        )
        return { ...c, messages: msgs }
      })
    } finally {
      setIsStreaming(false)
      // scroll to bottom
      setTimeout(() => scrollRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollIntoView({ behavior: 'smooth' }), 30)
  }, [activeConversation?.messages.length])

  return (
    <div className="flex h-screen w-full">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onNew={createNewConversation}
        onSelect={setActiveId}
      />

      <main className="flex h-full flex-1 flex-col">
        <div className="flex-1 overflow-auto">
          {activeConversation ? (
            <div>
              {activeConversation.messages
                .filter((m) => m.role !== 'system' || m.content)
                .map((m) => (
                  <div key={m.id} className={m.role === 'assistant' ? 'bg-white' : ''}>
                    <Message msg={m} />
                  </div>
                ))}
              <div ref={scrollRef} />
            </div>
          ) : (
            <div className="mx-auto max-w-3xl px-6 py-12">
              <h1 className="text-2xl font-semibold">EKA Brain</h1>
              <p className="mt-2 text-neutral-600">
                Start a new chat, or go to Documents to ingest your PDFs/DOCX.
              </p>
              <button
                onClick={createNewConversation}
                className="mt-6 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
              >
                New chat
              </button>
            </div>
          )}
        </div>

        <div className="border-t border-neutral-200 bg-white">
          <div className="mx-auto flex max-w-3xl gap-3 px-4 py-4">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void sendMessage()
                }
              }}
              placeholder="Message EKA…"
              className="min-h-[44px] flex-1 resize-none rounded-xl border border-neutral-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-neutral-200"
            />
            <button
              onClick={() => void sendMessage()}
              disabled={isStreaming || !activeId}
              className={
                'rounded-xl px-4 py-2 text-sm font-medium text-white ' +
                (isStreaming || !activeId
                  ? 'bg-neutral-300'
                  : 'bg-neutral-900 hover:bg-neutral-800')
              }
            >
              {isStreaming ? 'Streaming…' : 'Send'}
            </button>
          </div>
          <div className="mx-auto max-w-3xl px-4 pb-4 text-xs text-neutral-500">
            Enter to send • Shift+Enter for newline
          </div>
        </div>
      </main>
    </div>
  )
}
