export type SSEEvent = { event: string; data: string }

// Parses SSE blocks separated by \n\n.
export function parseSSE(buffer: string): { events: SSEEvent[]; rest: string } {
  const events: SSEEvent[] = []
  const parts = buffer.split('\n\n')

  // last part may be incomplete
  const rest = parts.pop() ?? ''

  for (const part of parts) {
    const lines = part.split('\n')
    let event = 'message'
    let dataLines: string[] = []

    for (const line of lines) {
      if (line.startsWith('event:')) {
        event = line.slice('event:'.length).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trim())
      }
    }

    const data = dataLines.join('\n')
    if (data.length > 0 || event !== 'message') {
      events.push({ event, data })
    }
  }

  return { events, rest }
}
