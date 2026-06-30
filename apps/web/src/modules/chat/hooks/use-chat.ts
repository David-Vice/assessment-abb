import { useCallback, useRef, useState } from 'react';

import { CHAT_URL } from '@/lib/api';
import { ChatResponseSchema } from '@/lib/schemas';
import type { AnswerStatus, Citation, Language } from '@/lib/schemas';
import { parseSSEBlock, splitSSEBuffer } from '@/lib/sse';

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

        if (!response.body) throw new Error('No response body');

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
            return; // malformed event — ignore
          }

          if (parsed.event === 'token') {
            const token = (payload as { token: string }).token;
            updateAssistant((m) => ({ ...m, content: m.content + token }));
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
              // Keep whatever streamed; just end the stream cleanly.
              updateAssistant((m) => ({ ...m, streaming: false }));
            }
          } else if (parsed.event === 'error') {
            const { detail } = payload as { detail: string };
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
          updateAssistant((m) => ({ ...m, error: 'Connection error', streaming: false }));
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, sessionId],
  );

  return { messages, isStreaming, send, clearMessages };
}
