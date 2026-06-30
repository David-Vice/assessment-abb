import { ExternalLink } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Badge } from '@/components/ui/badge';
import type { Citation, Segment } from '@/lib/schemas';

// Typed as Record<Segment, string> so adding a new segment enum member is a
// compile-time error here rather than a silent runtime miss.
const SEGMENT_COLORS: Record<Segment, string> = {
  individuals: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  business: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  about: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

interface CitationsPanelProps {
  citations: Citation[];
}

export function CitationsPanel({ citations }: CitationsPanelProps): React.JSX.Element {
  const { t } = useTranslation();

  return (
    <div className="space-y-1.5 w-full">
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
        {t('chat.citations')}
      </p>
      <div className="space-y-1">
        {citations.map((citation, i) => (
          <a
            key={i}
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-2 rounded-lg border bg-card px-3 py-2 text-xs hover:bg-accent transition-colors group"
          >
            <ExternalLink className="h-3 w-3 mt-0.5 shrink-0 text-muted-foreground group-hover:text-foreground" />
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{citation.title ?? citation.url}</p>
              {citation.snippet && (
                <p className="text-muted-foreground line-clamp-2 mt-0.5">{citation.snippet}</p>
              )}
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <span
                className={`text-[9px] font-semibold rounded px-1 py-0.5 uppercase ${SEGMENT_COLORS[citation.segment] ?? SEGMENT_COLORS.other}`}
              >
                {citation.segment}
              </span>
              <Badge variant="outline" className="text-[9px] h-4 px-1 uppercase">
                {citation.language}
              </Badge>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
