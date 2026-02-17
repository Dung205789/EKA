import { backendBaseUrl } from '@/lib/backend'

export async function POST(req: Request) {
  const body = await req.text()
  const upstream = await fetch(`${backendBaseUrl()}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body
  })

  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  })
}
