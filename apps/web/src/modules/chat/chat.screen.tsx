import { PlusCircle, Upload } from 'lucide-react';
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
}

export function ChatScreen({ onGoToUpload }: ChatScreenProps): React.JSX.Element {
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
      <Button variant="ghost" size="sm" onClick={onGoToUpload} className="gap-1.5 text-xs">
        <Upload className="h-3.5 w-3.5" />
        {t('nav.upload')}
      </Button>
      <Button variant="ghost" size="sm" onClick={handleNewChat} className="gap-1.5 text-xs">
        <PlusCircle className="h-3.5 w-3.5" />
        {t('chat.newChat')}
      </Button>
    </>
  );

  return (
    <div className="flex flex-col h-screen">
      <Header actions={headerActions} />

      {/* Message area */}
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin px-4 pt-4">
        {messages.length === 0 ? (
          <SuggestedQuestions onSelect={handleSuggestedQuestion} />
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Input bar */}
      <div className="shrink-0 border-t bg-card px-4 py-3">
        {isStreaming && (
          <p className="text-xs text-muted-foreground mb-2 animate-pulse text-center">
            {t('chat.thinking')}
          </p>
        )}
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
