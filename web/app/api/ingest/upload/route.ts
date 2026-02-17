import { backendBaseUrl } from '@/lib/backend'

export const runtime = 'nodejs'

export async function POST(req: Request) {
  const url = new URL(req.url)
  const mode = url.searchParams.get('mode') || 'auto'

  const form = await req.formData()
  const upstream = await fetch(`${backendBaseUrl()}/ingest/upload?mode=${encodeURIComponent(mode)}`, {
    method: 'POST',
    body: form
  })

  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  })
}
