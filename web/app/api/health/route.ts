import { backendBaseUrl } from '@/lib/backend'

export async function GET() {
  const upstream = await fetch(`${backendBaseUrl()}/health`, { cache: 'no-store' })
  const body = await upstream.text()
  return new Response(body, {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  })
}
