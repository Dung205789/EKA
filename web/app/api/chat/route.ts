import { backendBaseUrl } from '@/lib/backend'

export const runtime = 'nodejs'

export async function POST(req: Request) {
  let body = ''
  try {
    body = await req.text()
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid request body' }), {
      status: 400,
      headers: { 'content-type': 'application/json' }
    })
  }

  try {
    const upstream = await fetch(`${backendBaseUrl()}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body,
      cache: 'no-store'
    })

    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
    })
  } catch (e: any) {
    return new Response(
      JSON.stringify({ error: e?.message || 'Failed to reach backend /chat endpoint' }),
      {
        status: 502,
        headers: { 'content-type': 'application/json' }
      }
    )
  }
}
