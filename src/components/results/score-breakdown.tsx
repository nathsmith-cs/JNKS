"use client";

import { BlurFade } from "@/components/ui/blur-fade";
import type { CategoryScore } from "@/types/analysis";
import { ScoreCard } from "./score-card";

interface ScoreBreakdownProps {
  categories: CategoryScore[];
}

export function ScoreBreakdown({ categories }: ScoreBreakdownProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {categories.map((cat, i) => (
        <BlurFade key={cat.name} delay={0.1 * i} inView>
          <ScoreCard category={cat} delay={0.3 + i * 0.15} />
        </BlurFade>
      ))}
    </div>
  );
}
