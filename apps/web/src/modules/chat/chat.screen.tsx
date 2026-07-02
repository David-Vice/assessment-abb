import { BarChart3, PlusCircle, Upload } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { Header } from '@/modules/common/components/header';
import { useAppStore } from '@/store/app-store';

import { ChatInput } from './components/chat-input';
import { MessageList } from './components/message-list';
import { SuggestedQuestions } from './components/suggested-questions';
import { useChat } from './hooks/use-chat';

interface ChatScreenProps {
  onGoToUpload: () => void;
  onGoToDashboard: () => void;
  onLogoClick?: () => void;
}

export function ChatScreen({
  onGoToUpload,
  onGoToDashboard,
  onLogoClick,
}: ChatScreenProps): React.JSX.Element {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const sessionId = useAppStore((s) => s.sessionId);
  const resetSession = useAppStore((s) => s.resetSession);

  const { messages, isStreaming, send, clearMessages } = useChat(sessionId);

  const handleNewChat = () => {
    clearMessages();
    resetSession();
  };

  const handleSend = (text: string) => {
    void send(text, language);
  };

  const handleSuggestedQuestion = (q: string) => {
    void send(q, language);
  };

  const headerActions = (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={onGoToDashboard}
        className="h-10 w-10 shrink-0 sm:h-8 sm:w-auto sm:px-3"
        aria-label={t('nav.dashboard')}
      >
        <BarChart3 className="h-4 w-4" />
        <span className="hidden sm:inline sm:ml-1.5 sm:text-xs">{t('nav.dashboard')}</span>
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={onGoToUpload}
        className="h-10 w-10 shrink-0 sm:h-8 sm:w-auto sm:px-3"
        aria-label={t('nav.upload')}
      >
        <Upload className="h-4 w-4" />
        <span className="hidden sm:inline sm:ml-1.5 sm:text-xs">{t('nav.upload')}</span>
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={handleNewChat}
        className="h-10 w-10 shrink-0 sm:h-8 sm:w-auto sm:px-3"
        aria-label={t('chat.newChat')}
      >
        <PlusCircle className="h-4 w-4" />
        <span className="hidden sm:inline sm:ml-1.5 sm:text-xs">{t('chat.newChat')}</span>
      </Button>
    </>
  );

  return (
    <div className="abb-app-shell abb-page-bg">
      <Header actions={headerActions} onLogoClick={onLogoClick} />

      <div className="flex min-h-0 flex-1 flex-col px-2 sm:px-4">
        <div className="abb-shell">
          <div
            className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin px-0.5 pt-3 sm:px-1 sm:pt-4"
            role="log"
            aria-live="polite"
            aria-label={t('chat.conversation')}
          >
            {messages.length === 0 ? (
              <SuggestedQuestions onSelect={handleSuggestedQuestion} />
            ) : (
              <MessageList messages={messages} />
            )}
          </div>

          <div className="abb-input-bar">
            {isStreaming && (
              <p className="mb-2 text-center text-xs text-muted-foreground" aria-live="polite">
                {t('chat.thinking')}
              </p>
            )}
            <ChatInput onSend={handleSend} sendDisabled={isStreaming} />
            <p className="mt-2 px-1 text-center text-[10px] leading-relaxed text-muted-foreground sm:text-[11px]">
              {t('chat.disclaimer')}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
