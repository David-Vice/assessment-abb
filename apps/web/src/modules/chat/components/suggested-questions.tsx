import { Sparkles } from 'lucide-react';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';

interface SuggestedQuestionsProps {
  onSelect: (q: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps): React.JSX.Element {
  const { t } = useTranslation();
  const questions = t('chat.suggested', { returnObjects: true }) as string[];

  return (
    <div className="flex flex-col items-center gap-4 py-12 px-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Sparkles className="h-4 w-4" />
        <span className="text-sm font-medium">{t('chat.suggestedTitle')}</span>
      </div>
      <div className="flex flex-col gap-2 w-full max-w-md">
        {questions.map((q) => (
          <Button
            key={q}
            variant="outline"
            className="h-auto py-2.5 px-4 text-sm text-left justify-start whitespace-normal leading-snug"
            onClick={() => onSelect(q)}
          >
            {q}
          </Button>
        ))}
      </div>
    </div>
  );
}
