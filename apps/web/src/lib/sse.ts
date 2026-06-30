/**
 * Minimal SSE (Server-Sent Events) parsing helpers.
 *
 * The backend (`sse-starlette`) emits CRLF (`\r\n`) line endings, `\r\n\r\n`
 * event separators, and periodic `: ping` comment lines. These pure helpers
 * normalize all of that so the chat hook can stay focused on dispatch.
 */

export interface SSEEvent {
  event: string;
  data: string;
}

/**
 * Split an accumulated stream buffer into complete event blocks plus the
 * trailing incomplete block (which must be retained for the next read).
 */
export function splitSSEBuffer(buffer: string): { blocks: string[]; rest: string } {
  const parts = buffer.split(/\r?\n\r?\n/);
  const rest = parts.pop() ?? '';
  return { blocks: parts, rest };
}

/**
 * Parse a single event block into its event type and joined data payload.
 * Returns null for comment-only/empty blocks (e.g. `: ping`), which carry no data.
 */
export function parseSSEBlock(block: string): SSEEvent | null {
  let event = 'message';
  const dataParts: string[] = [];

  for (const rawLine of block.split('\n')) {
    const line = rawLine.replace(/\r$/, '');
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      // Per spec, a single leading space after the colon is stripped.
      dataParts.push(line.slice(5).replace(/^ /, ''));
    }
  }

  const data = dataParts.join('\n');
  return data ? { event, data } : null;
}
