import { backendBaseUrl } from '@/lib/backend'

export const runtime = 'nodejs'

export async function POST(req: Request) {
  const body = await req.text()

  const upstream = await fetch(`${backendBaseUrl()}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body
  })

  // Stream bytes through to the browser.
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive'
    }
  })
}
