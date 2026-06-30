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
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-1">
        {PRESETS.map((p) => (
          <Button
            key={p}
            variant={preset === p ? 'default' : 'outline'}
            size="sm"
            onClick={() => onPresetChange(p)}
            className="text-xs"
          >
            {t(`dashboard.range.${p}`)}
          </Button>
        ))}
      </div>

      <div className="flex items-center gap-1">
        {LANGS.map((l) => (
          <button
            key={l ?? 'all'}
            onClick={() => onLangChange(l)}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium uppercase transition-colors',
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
