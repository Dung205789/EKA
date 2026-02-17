'use client'

import Link from 'next/link'
import { Plus, MessageSquare, FileText } from 'lucide-react'
import type { Conversation } from '@/lib/types'

export function Sidebar({
  conversations,
  activeId,
  onNew,
  onSelect
}: {
  conversations: Conversation[]
  activeId: string | null
  onNew: () => void
  onSelect: (id: string) => void
}) {
  return (
    <aside className="flex h-full w-72 flex-col border-r border-neutral-200 bg-white">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="font-semibold">EKA Brain</div>
        <button
          onClick={onNew}
          className="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-sm hover:bg-neutral-50"
          title="New chat"
        >
          <Plus size={16} />
          New
        </button>
      </div>

      <nav className="px-2">
        <Link
          href="/"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-neutral-50"
        >
          <MessageSquare size={16} />
          Chat
        </Link>
        <Link
          href="/documents"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-neutral-50"
        >
          <FileText size={16} />
          Documents
        </Link>
      </nav>

      <div className="mt-3 px-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Conversations
      </div>

      <div className="flex-1 overflow-auto p-2">
        {conversations.length === 0 ? (
          <div className="px-3 py-2 text-sm text-neutral-500">
            No chats yet.
          </div>
        ) : (
          <ul className="space-y-1">
            {conversations
              .slice()
              .sort((a, b) => b.createdAt - a.createdAt)
              .map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => onSelect(c.id)}
                    className={
                      'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-neutral-50 ' +
                      (activeId === c.id ? 'bg-neutral-100' : '')
                    }
                  >
                    <MessageSquare size={16} className="shrink-0" />
                    <span className="line-clamp-1">{c.title}</span>
                  </button>
                </li>
              ))}
          </ul>
        )}
      </div>

      <div className="border-t border-neutral-200 p-3 text-xs text-neutral-500">
        Local-first • Streaming • RAG
      </div>
    </aside>
  )
}
