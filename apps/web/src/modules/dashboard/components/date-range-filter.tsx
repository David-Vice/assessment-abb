import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { Language } from '@/lib/schemas';
import type { RangePreset } from '../hooks/use-analytics';

interface DateRangeFilterProps {
  preset: RangePreset;
  onPresetChange: (p: RangePreset) => void;
  lang: Language | undefined;
  onLangChange: (l: Language | undefined) => void;
}

const PRESETS: RangePreset[] = ['24h', '7d', '30d'];
const LANGS: (Language | undefined)[] = [undefined, 'az', 'en', 'ru'];

export function DateRangeFilter({
  preset,
  onPresetChange,
  lang,
  onLangChange,
}: DateRangeFilterProps): React.JSX.Element {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
      <div className="flex w-full flex-wrap items-center gap-1 sm:w-auto">
        {PRESETS.map((p) => (
          <Button
            key={p}
            variant={preset === p ? 'default' : 'outline'}
            size="sm"
            onClick={() => onPresetChange(p)}
            className="min-h-10 flex-1 text-xs sm:min-h-8 sm:flex-none"
          >
            {t(`dashboard.range.${p}`)}
          </Button>
        ))}
      </div>

      <div className="flex w-full flex-wrap items-center gap-1 sm:w-auto">
        {LANGS.map((l) => (
          <button
            key={l ?? 'all'}
            onClick={() => onLangChange(l)}
            className={cn(
              'min-h-10 flex-1 rounded-md px-2.5 py-2 text-xs font-medium uppercase transition-colors sm:min-h-0 sm:flex-none sm:py-1',
              lang === l
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-accent',
            )}
          >
            {l ?? t('dashboard.allLanguages')}
          </button>
        ))}
      </div>
    </div>
  );
}
