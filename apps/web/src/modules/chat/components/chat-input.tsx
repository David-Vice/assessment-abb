import { SendHorizontal } from 'lucide-react';
import * as React from 'react';
import { useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (text: string) => void;
  /** Blocks send only — textarea stays editable so users can draft the next question. */
  sendDisabled?: boolean;
}

export function ChatInput({ onSend, sendDisabled = false }: ChatInputProps): React.JSX.Element {
  const { t } = useTranslation();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const value = textareaRef.current?.value.trim() ?? '';
    if (!value || sendDisabled) return;
    onSend(value);
    if (textareaRef.current) {
      textareaRef.current.value = '';
      textareaRef.current.style.height = 'auto';
    }
  }, [onSend, sendDisabled]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !sendDisabled) {
      e.preventDefault();
      submit();
    }
  };

  const autoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const el = e.currentTarget;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex items-end gap-2 rounded-2xl border border-border/80 bg-card p-2 shadow-soft">
      <div className="relative min-w-0 flex-1">
        <textarea
          ref={textareaRef}
          rows={1}
          onKeyDown={onKeyDown}
          onChange={autoResize}
          placeholder={t('chat.placeholder')}
          className={cn(
            'max-h-40 w-full resize-none rounded-xl border-0 bg-transparent px-3 py-2.5 text-sm leading-relaxed',
            'placeholder:text-muted-foreground focus-visible:outline-none',
          )}
          aria-label={t('chat.placeholder')}
        />
      </div>

      <Button
        onClick={submit}
        disabled={sendDisabled}
        size="icon"
        className="h-11 w-11 shrink-0 rounded-xl abb-gradient-bg text-primary-foreground hover:opacity-90"
        aria-label={t('chat.send')}
      >
        {sendDisabled ? (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
        ) : (
          <SendHorizontal className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}
