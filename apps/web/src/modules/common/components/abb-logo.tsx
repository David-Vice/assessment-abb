import * as React from 'react';

export function AbbLogo({ size = 32 }: { size?: number }): React.JSX.Element {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="ABB"
    >
      <rect width="32" height="32" rx="4" fill="hsl(var(--primary))" />
      <text
        x="50%"
        y="54%"
        dominantBaseline="middle"
        textAnchor="middle"
        fill="white"
        fontFamily="system-ui, sans-serif"
        fontWeight="700"
        fontSize="10"
        letterSpacing="0.5"
      >
        ABB
      </text>
    </svg>
  );
}
