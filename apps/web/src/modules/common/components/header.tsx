import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { AbbLogo } from './abb-logo';
import { LanguageSwitcher } from './language-switcher';
import { ThemeToggle } from './theme-toggle';

interface HeaderProps {
  actions?: React.ReactNode;
}

export function Header({ actions }: HeaderProps): React.JSX.Element {
  const { t } = useTranslation();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-4">
      <div className="flex items-center gap-2.5">
        <AbbLogo size={28} />
        <span className="text-base font-semibold tracking-tight">
          {t('common.abbAssistant')}
        </span>
      </div>

      <div className="flex items-center gap-2">
        {actions}
        <LanguageSwitcher />
        <ThemeToggle />
      </div>
    </header>
  );
}
