import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useAppStore } from '@/store/app-store';
import { ChatScreen } from '@/modules/chat/chat.screen';
import { DashboardScreen } from '@/modules/dashboard/dashboard.screen';
import { UploadScreen } from '@/modules/upload/upload.screen';

type AppView = 'chat' | 'dashboard' | 'upload';

export function App(): React.JSX.Element {
  const theme = useAppStore((s) => s.theme);
  const language = useAppStore((s) => s.language);
  const corpusStatus = useAppStore((s) => s.corpusStatus);
  const [view, setView] = useState<AppView>('chat');

  const { i18n } = useTranslation();

  const goToChat = useCallback(() => {
    setView('chat');
  }, []);

  // Sync Tailwind dark class with persisted theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  // Sync i18next language with persisted language
  useEffect(() => {
    void i18n.changeLanguage(language);
  }, [language, i18n]);

  if (corpusStatus !== 'ready') {
    return <UploadScreen />;
  }

  if (view === 'dashboard') {
    return <DashboardScreen onGoToChat={goToChat} onLogoClick={goToChat} />;
  }

  if (view === 'upload') {
    return <UploadScreen onLogoClick={goToChat} />;
  }

  return (
    <ChatScreen
      onLogoClick={goToChat}
      onGoToUpload={() => setView('upload')}
      onGoToDashboard={() => setView('dashboard')}
    />
  );
}
