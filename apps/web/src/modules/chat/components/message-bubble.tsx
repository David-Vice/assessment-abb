import * as React from 'react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '../hooks/use-chat';
import { CitationsPanel } from './citations-panel';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps): React.JSX.Element {
  const [showCitations, setShowCitations] = useState(false);
  const isUser = message.role === 'user';
  const isDeclined =
    message.status === 'declined_off_topic' || message.status === 'declined_injection';
  const hasCitations = (message.citations?.length ?? 0) > 0;

  return (
    <div className={cn('flex gap-3 mb-4', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="flex-shrink-0 mt-0.5">
          <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center">
            <span className="text-[10px] font-bold text-primary-foreground">ABB</span>
          </div>
        </div>
      )}

      <div className={cn('max-w-[75%] space-y-1.5', isUser && 'items-end flex flex-col')}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5 text-sm',
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-sm'
              : 'bg-card border rounded-bl-sm',
            isDeclined && 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300',
            message.error && 'bg-destructive/10 border-destructive/30 text-destructive',
          )}
        >
          {message.streaming && !message.content ? (
            <span className="flex gap-1 items-center text-muted-foreground py-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce" />
            </span>
          ) : message.error ? (
            <p>{message.error}</p>
          ) : isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations toggle */}
        {!message.streaming && hasCitations && (
          <button
            onClick={() => setShowCitations((v) => !v)}
            className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
          >
            <Badge variant="outline" className="text-[10px] h-4 px-1.5 cursor-pointer">
              {message.citations!.length} source{message.citations!.length !== 1 ? 's' : ''}
            </Badge>
            <span>{showCitations ? '▲' : '▼'}</span>
          </button>
        )}

        {showCitations && hasCitations && (
          <CitationsPanel citations={message.citations!} />
        )}
      </div>
    </div>
  );
}
