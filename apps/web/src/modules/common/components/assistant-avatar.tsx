import * as React from 'react';

import { AbbLogo } from '@/modules/common/components/abb-logo';
import { cn } from '@/lib/utils';

interface AssistantAvatarProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const HEIGHTS = {
  sm: 28,
  md: 32,
  lg: 48,
} as const;

export function AssistantAvatar({
  size = 'md',
  className,
}: AssistantAvatarProps): React.JSX.Element {
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-2xl bg-white p-1.5 shadow-soft ring-1 ring-border/80 dark:bg-card',
        size === 'lg' && 'p-2.5',
        className,
      )}
      aria-hidden="true"
    >
      <AbbLogo variant="mark" height={HEIGHTS[size]} />
    </div>
  );
}
