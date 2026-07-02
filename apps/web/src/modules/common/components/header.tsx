import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { AbbLogo } from './abb-logo';
import { LanguageSwitcher } from './language-switcher';
import { ThemeToggle } from './theme-toggle';

interface HeaderProps {
  actions?: React.ReactNode;
  onLogoClick?: () => void;
}

export function Header({ actions, onLogoClick }: HeaderProps): React.JSX.Element {
  const { t } = useTranslation();

  const logo = (
    <>
      <AbbLogo height={22} className="shrink-0 sm:hidden" />
      <AbbLogo height={26} className="hidden shrink-0 sm:block" />
    </>
  );

  return (
    <header className="sticky top-0 z-20 shrink-0 border-b border-border/80 abb-glass abb-safe-top">
      <div className="flex min-h-[3.5rem] items-center justify-between gap-2 px-3 py-2 sm:min-h-[3.75rem] sm:px-6 sm:py-0">
        <div className="flex min-w-0 flex-1 items-center gap-2 sm:gap-3">
          {onLogoClick ? (
            <button
              type="button"
              onClick={onLogoClick}
              className="shrink-0 rounded-lg transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              aria-label={t('nav.chat')}
            >
              {logo}
            </button>
          ) : (
            logo
          )}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              <span className="truncate text-sm font-semibold tracking-tight text-foreground sm:text-base">
                <span className="max-[400px]:hidden">{t('common.abbAssistant')}</span>
                <span className="hidden max-[400px]:inline">ABB AI</span>
              </span>
            </div>
            <p className="hidden truncate text-[11px] text-muted-foreground md:block">
              {t('common.tagline')}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-0.5 sm:gap-2">
          {actions}
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
