'use client'

import type { ChatMessage, Citation } from '@/lib/types'

function CitationCard({ c }: { c: Citation }) {
  const title = c.title || c.source || c.doc_id || 'Source'
  const meta = [c.page != null ? `p.${c.page}` : null, c.score != null ? `score ${c.score.toFixed?.(3) ?? c.score}` : null]
    .filter(Boolean)
    .join(' · ')

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-3">
      <div className="text-sm font-medium">{title}</div>
      {meta ? <div className="mt-1 text-xs text-neutral-500">{meta}</div> : null}
      {c.snippet ? <div className="mt-2 text-sm text-neutral-700 line-clamp-4">{c.snippet}</div> : null}
    </div>
  )
}

export function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  const isThinking = msg.role === 'assistant' && msg.thinking && !msg.content

  return (
    <div className={"mx-auto w-full max-w-3xl px-4 py-5"}>
      <div className={"flex gap-4"}>
        <div
          className={
            'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ' +
            (isUser ? 'bg-neutral-900 text-white' : 'bg-emerald-600 text-white')
          }
        >
          {isUser ? 'You' : 'EKA'}
        </div>

        <div className="min-w-0 flex-1">
          <div
            className={
              'whitespace-pre-wrap leading-relaxed ' +
              (isUser ? 'text-neutral-900' : 'text-neutral-900')
            }
          >
            {isThinking ? (
              <span className="text-neutral-500 italic">Thinking…</span>
            ) : (
              msg.content
            )}
          </div>

          {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 ? (
            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-medium text-neutral-700 hover:text-neutral-900">
                Sources ({msg.citations.length})
              </summary>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                {msg.citations.map((c, idx) => (
                  <CitationCard key={idx} c={c} />
                ))}
              </div>
            </details>
          ) : null}
        </div>
      </div>
    </div>
  )
}
