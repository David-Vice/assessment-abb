import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { useAppStore } from '@/store/app-store';
import { ChatScreen } from '@/modules/chat/chat.screen';
import { UploadScreen } from '@/modules/upload/upload.screen';

export function App(): React.JSX.Element {
  const theme = useAppStore((s) => s.theme);
  const language = useAppStore((s) => s.language);
  const corpusStatus = useAppStore((s) => s.corpusStatus);

  const { i18n } = useTranslation();

  // Sync Tailwind dark class with persisted theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  // Sync i18next language with persisted language
  useEffect(() => {
    void i18n.changeLanguage(language);
  }, [language, i18n]);

  if (corpusStatus === 'ready') {
    return <ChatScreen onGoToUpload={() => useAppStore.getState().resetCorpus()} />;
  }

  return <UploadScreen />;
}
