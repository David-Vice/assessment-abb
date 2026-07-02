import * as React from 'react';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';

import { Badge } from '@/components/ui/badge';
import { AbbLogo } from '@/modules/common/components/abb-logo';
import { cn } from '@/lib/utils';
import type { ChatMessage } from '../hooks/use-chat';
import { CitationsPanel } from './citations-panel';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps): React.JSX.Element {
  const { t } = useTranslation();
  const [showCitations, setShowCitations] = useState(false);
  const isUser = message.role === 'user';
  const isDeclined =
    message.status === 'declined_off_topic' || message.status === 'declined_injection';
  const hasCitations = (message.citations?.length ?? 0) > 0;

  return (
    <div
      className={cn(
        'mb-4 flex items-start animate-fade-in gap-2 sm:mb-5 sm:gap-3',
        isUser ? 'justify-end' : 'justify-start',
      )}
      aria-label={isUser ? t('chat.you') : t('common.abbAssistant')}
    >
      {!isUser && (
        <div className="mt-5 shrink-0 self-start sm:mt-6">
          <AbbLogo variant="mark" height={24} />
        </div>
      )}

      <div
        className={cn(
          'max-w-[92%] space-y-1.5 sm:max-w-[85%] md:max-w-[78%]',
          isUser && 'flex flex-col items-end',
        )}
      >
        {!isUser && (
          <span className="text-[10px] font-medium text-muted-foreground sm:text-[11px]">
            {t('common.abbAssistant')}
          </span>
        )}

        <div
          className={cn(
            'rounded-2xl px-3.5 py-2.5 text-sm shadow-bubble sm:px-4 sm:py-3',
            isUser
              ? 'rounded-br-md abb-gradient-bg text-primary-foreground'
              : 'rounded-bl-md border border-border/80 bg-card text-foreground',
            isDeclined &&
              'border-amber-200 bg-amber-50 text-amber-900 shadow-none dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200',
            message.error &&
              'border-destructive/30 bg-destructive/10 text-destructive shadow-none',
          )}
        >
          {message.streaming && !message.content ? (
            <span className="flex items-center gap-1 py-0.5 text-muted-foreground" aria-live="polite">
              <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-primary" />
            </span>
          ) : message.error ? (
            <p className="text-sm leading-relaxed">{t(message.error, { defaultValue: message.error })}</p>
          ) : isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed sm:text-sm">{message.content}</p>
          ) : (
            <div className="prose-chat text-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {!message.streaming && hasCitations && (
          <button
            type="button"
            onClick={() => setShowCitations((v) => !v)}
            className="flex min-h-11 items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground sm:min-h-0"
            aria-expanded={showCitations}
          >
            <Badge
              variant="outline"
              className="h-5 cursor-pointer border-primary/20 bg-primary/5 px-2 text-[10px] text-primary"
            >
              {t('chat.sourcesCount', { count: message.citations!.length })}
            </Badge>
            <span aria-hidden="true">{showCitations ? '▲' : '▼'}</span>
          </button>
        )}

        {showCitations && hasCitations && <CitationsPanel citations={message.citations!} />}
      </div>
    </div>
  );
}
