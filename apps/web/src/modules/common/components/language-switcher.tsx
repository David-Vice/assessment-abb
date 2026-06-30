import * as React from 'react';

import { cn } from '@/lib/utils';
import type { Language } from '@/lib/schemas';
import { useAppStore } from '@/store/app-store';

const LANGS: { code: Language; label: string }[] = [
  { code: 'az', label: 'AZ' },
  { code: 'en', label: 'EN' },
  { code: 'ru', label: 'RU' },
];

export function LanguageSwitcher(): React.JSX.Element {
  const language = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);

  return (
    <div className="flex items-center rounded-md border border-input overflow-hidden text-xs font-medium">
      {LANGS.map(({ code, label }) => (
        <button
          key={code}
          onClick={() => setLanguage(code)}
          className={cn(
            'px-2.5 py-1 transition-colors',
            language === code
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-muted-foreground hover:text-foreground hover:bg-accent',
          )}
          aria-pressed={language === code}
          aria-label={`Switch to ${label}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
