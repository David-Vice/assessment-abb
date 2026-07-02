import { ShieldCheck, Sparkles } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { AbbLogo } from '@/modules/common/components/abb-logo';
import { cn } from '@/lib/utils';

interface SuggestedQuestionsProps {
  onSelect: (q: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps): React.JSX.Element {
  const { t } = useTranslation();
  const questions = t('chat.suggested', { returnObjects: true }) as string[];

  return (
    <div
      className="flex animate-fade-in flex-col items-center gap-6 px-1 py-6 sm:gap-8 sm:px-2 sm:py-12"
      role="region"
      aria-label={t('chat.suggestedTitle')}
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <AbbLogo height={36} className="sm:hidden" />
        <AbbLogo height={44} className="hidden sm:block" />
        <div className="space-y-2">
          <h2 className="text-lg font-semibold tracking-tight sm:text-2xl">
            {t('chat.welcomeTitle')}
          </h2>
          <p className="max-w-md text-sm leading-relaxed text-muted-foreground">
            {t('chat.welcomeSubtitle')}
          </p>
        </div>
      </div>

      <div className="grid w-full max-w-lg gap-2 sm:grid-cols-2">
        <CapabilityCard icon={Sparkles} text={t('chat.capabilities.can')} />
        <CapabilityCard icon={ShieldCheck} text={t('chat.capabilities.cannot')} />
      </div>

      <div className="w-full max-w-lg space-y-3">
        <p className="flex items-center justify-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5" />
          {t('chat.suggestedTitle')}
        </p>
        <div className="flex w-full flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-center">
          {questions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => onSelect(q)}
              className={cn(
                'min-h-11 w-full rounded-full border border-border bg-card px-3 py-2.5 text-left text-sm leading-snug text-foreground shadow-sm sm:min-h-11 sm:w-auto sm:max-w-full sm:px-4',
                'transition-all hover:border-primary/40 hover:bg-accent hover:shadow-soft',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
              )}
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function CapabilityCard({
  icon: Icon,
  text,
}: {
  icon: React.ComponentType<{ className?: string }>;
  text: string;
}): React.JSX.Element {
  return (
    <div className="flex gap-2.5 rounded-2xl border border-border/80 bg-card/80 p-3.5 text-left shadow-sm">
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      <p className="text-xs leading-relaxed text-muted-foreground">{text}</p>
    </div>
  );
}
