"use client";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { MagicCard } from "@/components/ui/magic-card";
import { NumberTicker } from "@/components/ui/number-ticker";
import { useAccentColor } from "@/components/accent-color-provider";
import type { CategoryScore } from "@/types/analysis";

interface ScoreCardProps {
  category: CategoryScore;
  delay: number;
}

const badgeVariant: Record<
  CategoryScore["label"],
  "default" | "secondary" | "destructive" | "outline"
> = {
  Excellent: "default",
  Good: "secondary",
  "Needs Work": "outline",
  Poor: "destructive",
};

export function ScoreCard({ category, delay }: ScoreCardProps) {
  const { accent } = useAccentColor();

  return (
    <MagicCard
      className="cursor-default"
      gradientColor={`rgba(${accent.rgb}, 0.06)`}
      gradientFrom={accent.hex}
      gradientTo={accent.hexDark}
    >
      <div className="p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">{category.name}</h3>
          <Badge variant={badgeVariant[category.label]}>{category.label}</Badge>
        </div>
        <div className="flex items-center gap-3">
          <Progress value={category.score} className="flex-1" />
          <span className="text-sm font-semibold w-10 text-right tabular-nums">
            <NumberTicker value={category.score} delay={delay} />
            <span className="text-muted-foreground">%</span>
          </span>
        </div>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {category.tip}
        </p>
        {category.feedback && (category.feedback.strengths.length > 0 || category.feedback.issues.length > 0) && (
          <div className="space-y-2 pt-2 border-t border-border/30">
            {category.feedback.strengths.length > 0 && (
              <div>
                <p className="text-xs font-medium text-emerald-500">Strengths</p>
                <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                  {category.feedback.strengths.map((s, i) => (
                    <li key={i}>- {s}</li>
                  ))}
                </ul>
              </div>
            )}
            {category.feedback.issues.length > 0 && (
              <div>
                <p className="text-xs font-medium text-amber-500">Areas to Improve</p>
                <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                  {category.feedback.issues.map((s, i) => (
                    <li key={i}>- {s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </MagicCard>
  );
}
