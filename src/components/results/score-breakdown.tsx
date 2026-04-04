import type { CategoryScore } from "@/types/analysis";
import { ScoreCard } from "./score-card";

interface ScoreBreakdownProps {
  categories: CategoryScore[];
}

export function ScoreBreakdown({ categories }: ScoreBreakdownProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {categories.map((cat) => (
        <ScoreCard key={cat.name} category={cat} />
      ))}
    </div>
  );
}
