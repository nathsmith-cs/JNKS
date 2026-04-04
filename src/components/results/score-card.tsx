import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { CategoryScore } from "@/types/analysis";

interface ScoreCardProps {
  category: CategoryScore;
}

const badgeVariant: Record<CategoryScore["label"], "default" | "secondary" | "destructive" | "outline"> = {
  Excellent: "default",
  Good: "secondary",
  "Needs Work": "outline",
  Poor: "destructive",
};

export function ScoreCard({ category }: ScoreCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{category.name}</CardTitle>
          <Badge variant={badgeVariant[category.label]}>{category.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-3">
          <Progress value={category.score} className="flex-1" />
          <span className="text-sm font-semibold w-10 text-right">
            {category.score}%
          </span>
        </div>
        <p className="text-sm text-muted-foreground">{category.tip}</p>
      </CardContent>
    </Card>
  );
}
