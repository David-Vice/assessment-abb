import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import {
  getAnalyticsDistribution,
  getAnalyticsPerformance,
  getAnalyticsQuality,
  getAnalyticsSummary,
  getAnalyticsTopQuestions,
  getAnalyticsVolume,
} from '@/lib/api';
import type { AnalyticsFilters } from '@/lib/api';
import type { Language } from '@/lib/schemas';

export type RangePreset = '24h' | '7d' | '30d';

interface ResolvedRange {
  from: string;
  to: string;
  bucket: 'hour' | 'day';
}

function resolveRange(preset: RangePreset): ResolvedRange {
  const to = new Date();
  const from = new Date(to);
  if (preset === '24h') {
    from.setHours(from.getHours() - 24);
    return { from: from.toISOString(), to: to.toISOString(), bucket: 'hour' };
  }
  from.setDate(from.getDate() - (preset === '7d' ? 7 : 30));
  return { from: from.toISOString(), to: to.toISOString(), bucket: 'day' };
}

export function useAnalytics() {
  const [preset, setPreset] = useState<RangePreset>('7d');
  const [lang, setLang] = useState<Language | undefined>(undefined);

  const { from, to, bucket } = useMemo(() => resolveRange(preset), [preset]);
  const filters: AnalyticsFilters = useMemo(() => ({ from, to, lang }), [from, to, lang]);
  const baseKey = [from, to, lang ?? 'all'] as const;

  const summary = useQuery({
    queryKey: ['analytics', 'summary', ...baseKey],
    queryFn: () => getAnalyticsSummary(filters),
  });
  const performance = useQuery({
    queryKey: ['analytics', 'performance', ...baseKey],
    queryFn: () => getAnalyticsPerformance(filters),
  });
  const volume = useQuery({
    queryKey: ['analytics', 'volume', ...baseKey, bucket],
    queryFn: () => getAnalyticsVolume(filters, bucket),
  });
  const quality = useQuery({
    queryKey: ['analytics', 'quality', ...baseKey],
    queryFn: () => getAnalyticsQuality(filters),
  });
  const distribution = useQuery({
    queryKey: ['analytics', 'distribution', ...baseKey],
    queryFn: () => getAnalyticsDistribution(filters),
  });
  const topQuestions = useQuery({
    queryKey: ['analytics', 'top-questions', ...baseKey],
    queryFn: () => getAnalyticsTopQuestions(filters),
  });

  return {
    preset,
    setPreset,
    lang,
    setLang,
    from,
    to,
    summary,
    performance,
    volume,
    quality,
    distribution,
    topQuestions,
  };
}
