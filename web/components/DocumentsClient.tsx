'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/Sidebar'
import type { Conversation } from '@/lib/types'

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

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16)
}

type Doc = {
  id: string
  title: string
  source: string
  created_at?: string
}

export function DocumentsClient() {
  const router = useRouter()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [docs, setDocs] = useState<Doc[]>([])
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'auto' | 'general' | 'legal'>('auto')
  const [status, setStatus] = useState<string>('')
  const [url, setUrl] = useState<string>('')

  useEffect(() => {
    const convs = loadConversations()
    setConversations(convs)
    const savedActive = localStorage.getItem(LS_ACTIVE)
    setActiveId(savedActive)
    void refreshDocs()
  }, [])

  async function refreshDocs() {
    try {
      const r = await fetch('/api/documents')
      if (!r.ok) throw new Error(await r.text())
      const data = await r.json()
      setDocs(data)
    } catch (e: any) {
      setStatus(e?.message || String(e))
    }
  }

  function newChat() {
    const c: Conversation = {
      id: uid(),
      title: 'New chat',
      createdAt: Date.now(),
      messages: []
    }
    const next = [c, ...conversations]
    localStorage.setItem(LS_KEY, JSON.stringify(next))
    localStorage.setItem(LS_ACTIVE, c.id)
    router.push('/')
  }

  function selectChat(id: string) {
    localStorage.setItem(LS_ACTIVE, id)
    setActiveId(id)
    router.push('/')
  }

  async function uploadFile(file: File) {
    setBusy(true)
    setStatus('')
    try {
      const form = new FormData()
      form.append('file', file)
      const r = await fetch(`/api/ingest/upload?mode=${mode}`, {
        method: 'POST',
        body: form
      })
      if (!r.ok) {
        const txt = await r.text()
        throw new Error(txt)
      }
      const data = await r.json()
      setStatus(`Ingested: ${data?.doc_id || 'ok'}`)
      await refreshDocs()
    } catch (e: any) {
      setStatus(e?.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  async function ingestUrl() {
    const u = url.trim()
    if (!u) return
    setBusy(true)
    setStatus('')
    try {
      const r = await fetch('/api/ingest/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: u, mode, source: 'auto' })
      })
      if (!r.ok) {
        const txt = await r.text()
        throw new Error(txt)
      }
      const data = await r.json()
      setStatus(`Ingested URL: ${data?.doc_id || 'ok'}`)
      setUrl('')
      await refreshDocs()
    } catch (e: any) {
      setStatus(e?.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  async function deleteDoc(id: string) {
    if (busy) return
    setBusy(true)
    setStatus('')
    try {
      const r = await fetch(`/api/documents/${id}`, { method: 'DELETE' })
      if (!r.ok) throw new Error(await r.text())
      await refreshDocs()
    } catch (e: any) {
      setStatus(e?.message || String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex h-screen w-full">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onNew={newChat}
        onSelect={selectChat}
      />

      <main className="flex h-full flex-1 flex-col">
        <div className="border-b border-neutral-200 bg-white px-6 py-4">
          <h1 className="text-lg font-semibold">Documents</h1>
          <p className="mt-1 text-sm text-neutral-600">
            Upload PDFs/DOCX/TXT to build your local knowledge base.
          </p>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-4xl space-y-6">
            <section className="rounded-2xl border border-neutral-200 bg-white p-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="text-sm font-medium">Upload</div>
                  <div className="text-xs text-neutral-500">Modes: auto / general / legal</div>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={mode}
                    onChange={(e) => setMode(e.target.value as any)}
                    className="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
                  >
                    <option value="auto">auto</option>
                    <option value="general">general</option>
                    <option value="legal">legal</option>
                  </select>

                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800">
                    <input
                      type="file"
                      className="hidden"
                      accept=".pdf,.docx,.txt,.md"
                      disabled={busy}
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) void uploadFile(f)
                        e.currentTarget.value = ''
                      }}
                    />
                    {busy ? 'Working…' : 'Choose file'}
                  </label>
                </div>
              </div>

              {status ? (
                <pre className="mt-4 whitespace-pre-wrap rounded-lg bg-neutral-50 p-3 text-xs text-neutral-700">
                  {status}
                </pre>
              ) : null}
            </section>

            <section className="rounded-2xl border border-neutral-200 bg-white p-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="text-sm font-medium">Ingest from URL</div>
                  <div className="text-xs text-neutral-500">
                    Supports web pages, PDF/DOCX links, and YouTube transcripts.
                  </div>
                </div>

                <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-center">
                  <input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://…"
                    className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm md:w-[420px]"
                  />
                  <button
                    disabled={busy || !url.trim()}
                    onClick={() => void ingestUrl()}
                    className={
                      'rounded-lg px-3 py-2 text-sm font-medium text-white ' +
                      (busy || !url.trim() ? 'bg-neutral-300' : 'bg-neutral-900 hover:bg-neutral-800')
                    }
                  >
                    {busy ? 'Working…' : 'Ingest URL'}
                  </button>
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-neutral-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium">Library</div>
                <button
                  onClick={() => void refreshDocs()}
                  className="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm hover:bg-neutral-50"
                >
                  Refresh
                </button>
              </div>

              <div className="mt-4 overflow-hidden rounded-xl border border-neutral-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-neutral-50 text-xs text-neutral-600">
                    <tr>
                      <th className="px-3 py-2">Title</th>
                      <th className="px-3 py-2">Source</th>
                      <th className="px-3 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.length === 0 ? (
                      <tr>
                        <td className="px-3 py-4 text-neutral-500" colSpan={3}>
                          No documents yet.
                        </td>
                      </tr>
                    ) : (
                      docs.map((d) => (
                        <tr key={d.id} className="border-t border-neutral-200">
                          <td className="px-3 py-2">{d.title}</td>
                          <td className="px-3 py-2 text-neutral-600">{d.source}</td>
                          <td className="px-3 py-2">
                            <button
                              onClick={() => void deleteDoc(d.id)}
                              className="rounded-lg border border-neutral-200 px-2 py-1 text-xs hover:bg-neutral-50"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  )
}
