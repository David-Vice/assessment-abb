import { useCallback, useEffect, useRef, useState } from 'react';
import { z } from 'zod';

import { CHAT_URL, getSession } from '@/lib/api';
import { ChatResponseSchema } from '@/lib/schemas';
import type { AnswerStatus, ChatTurn, Citation, Language } from '@/lib/schemas';
import { parseSSEBlock, splitSSEBuffer } from '@/lib/sse';

// Inline schemas for the two remaining SSE event payloads — consistent with the
// safeParse pattern already used for 'done', removes the two unchecked casts.
const TokenPayloadSchema = z.object({ token: z.string() });
const ErrorPayloadSchema = z.object({ detail: z.string() });

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
  citations?: Citation[];
  status?: AnswerStatus;
  error?: string;
}

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Restore conversation from the backend whenever the session changes.
  useEffect(() => {
    let cancelled = false;
    getSession(sessionId)
      .then((turns: ChatTurn[]) => {
        if (cancelled) return;
        setMessages(
          turns.flatMap((turn) => [
            { id: `${turn.id}-q`, role: 'user', content: turn.question },
            {
              id: `${turn.id}-a`,
              role: 'assistant',
              content: turn.answer,
              citations: turn.citations,
              status: turn.status,
            },
          ]),
        );
      })
      .catch(() => {}); // empty history on a new session is fine
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Cancel any in-flight stream when the component unmounts.
  useEffect(() => () => { abortRef.current?.abort(); }, []);

  const clearMessages = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setIsStreaming(false);
  }, []);

  const send = useCallback(
    async (question: string, language: Language) => {
      if (isStreaming) return;

      const assistantId = crypto.randomUUID();

      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: question },
        { id: assistantId, role: 'assistant', content: '', streaming: true },
      ]);
      setIsStreaming(true);

      abortRef.current = new AbortController();
      const signal = abortRef.current.signal;

      const updateAssistant = (updater: (m: ChatMessage) => ChatMessage) => {
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? updater(m) : m)));
      };

      try {
        const response = await fetch(`${CHAT_URL}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, question, language }),
          signal,
        });

        // A non-OK response (422, 503, …) returns JSON, not SSE — reading it as a
        // stream would drain silently with no terminal event and freeze the bubble.
        if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const dispatch = (block: string): void => {
          const parsed = parseSSEBlock(block);
          if (!parsed) return; // comment / ping / empty

          let payload: unknown;
          try {
            payload = JSON.parse(parsed.data);
          } catch {
            return; // malformed JSON — ignore
          }

          if (parsed.event === 'token') {
            const result = TokenPayloadSchema.safeParse(payload);
            if (result.success) {
              updateAssistant((m) => ({ ...m, content: m.content + result.data.token }));
            }
          } else if (parsed.event === 'done') {
            const result = ChatResponseSchema.safeParse(payload);
            if (result.success) {
              const resp = result.data;
              updateAssistant((m) => ({
                ...m,
                content: resp.answer,
                citations: resp.citations,
                status: resp.status,
                streaming: false,
              }));
            } else {
              // Keep whatever streamed; end cleanly.
              updateAssistant((m) => ({ ...m, streaming: false }));
            }
          } else if (parsed.event === 'error') {
            const result = ErrorPayloadSchema.safeParse(payload);
            const detail = result.success ? result.data.detail : 'chat.error';
            updateAssistant((m) => ({ ...m, error: detail, streaming: false }));
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const { blocks, rest } = splitSSEBuffer(buffer);
          buffer = rest; // retain the incomplete tail for the next read
          for (const block of blocks) dispatch(block);
        }

        // Flush any trailing complete event left without a final blank line.
        if (buffer.trim()) dispatch(buffer);
      } catch {
        if (!signal.aborted) {
          // 'chat.error' is resolved by MessageBubble via i18next; server detail
          // strings (already translated by the backend) are displayed as-is.
          updateAssistant((m) => ({ ...m, error: 'chat.error', streaming: false }));
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, sessionId],
  );

  return { messages, isStreaming, send, clearMessages };
}
