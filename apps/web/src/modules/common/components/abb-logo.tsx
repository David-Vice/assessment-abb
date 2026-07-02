import * as React from 'react';

import abbLogoSvg from '@/assets/abb-logo.svg?raw';
import abbMarkSvg from '@/assets/abb-mark.svg?raw';
import { cn } from '@/lib/utils';

const LOGO_ASPECT = 89 / 40;

interface AbbLogoProps {
  /** Height in pixels (width scales from official 89:40 aspect ratio). */
  height?: number;
  /** `full` — symbol + wordmark + tagline; `mark` — network symbol only. */
  variant?: 'full' | 'mark';
  className?: string;
}

export function AbbLogo({
  height = 28,
  variant = 'full',
  className,
}: AbbLogoProps): React.JSX.Element {
  const width = Math.round(height * (variant === 'full' ? LOGO_ASPECT : 1));
  const svg = variant === 'full' ? abbLogoSvg : abbMarkSvg;
  const viewBox = variant === 'full' ? '0 0 89 40' : '0 0 40 40';

  return (
    <span
      role="img"
      aria-label="ABB Bank"
      className={cn('inline-block shrink-0 text-primary', className)}
      style={{ width, height, lineHeight: 0 }}
      // Official ABB SVG from abb-bank.az — currentColor inherits brand primary.
      dangerouslySetInnerHTML={{
        __html: svg.replace(
          /<svg[^>]*>/,
          `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}" width="${width}" height="${height}" fill="none" class="h-full w-full">`,
        ),
      }}
    />
  );
}
