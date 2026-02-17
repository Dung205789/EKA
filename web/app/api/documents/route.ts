import { backendBaseUrl } from '@/lib/backend'

export async function GET() {
  const upstream = await fetch(`${backendBaseUrl()}/documents/`, { cache: 'no-store' })
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  })
}
