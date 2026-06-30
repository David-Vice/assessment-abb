import * as React from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ChartCardProps {
  title: string;
  isEmpty?: boolean;
  emptyText?: string;
  children: React.ReactNode;
}

export function ChartCard({
  title,
  isEmpty,
  emptyText,
  children,
}: ChartCardProps): React.JSX.Element {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {isEmpty ? (
          <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
            {emptyText}
          </div>
        ) : (
          <div className="h-[240px] w-full">{children}</div>
        )}
      </CardContent>
    </Card>
  );
}

// Shared categorical palette (works in light + dark). Index-stable so a given
// series keeps its color across renders.
export const CHART_COLORS = ['#1B63ED', '#7C3AED', '#10B981', '#F59E0B', '#EF4444', '#6B7280'];

// Neutral axis/grid color readable on both themes (mid-gray).
export const AXIS_COLOR = '#9CA3AF';
