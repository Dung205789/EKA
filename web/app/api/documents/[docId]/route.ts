import { backendBaseUrl } from '@/lib/backend'

export async function GET(_req: Request, { params }: { params: { docId: string } }) {
  const upstream = await fetch(`${backendBaseUrl()}/documents/${params.docId}`, { cache: 'no-store' })
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  })
}

export async function DELETE(_req: Request, { params }: { params: { docId: string } }) {
  const upstream = await fetch(`${backendBaseUrl()}/documents/${params.docId}`, { method: 'DELETE' })
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' }
  })
}
