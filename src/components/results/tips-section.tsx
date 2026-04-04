import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import type { CategoryScore } from "@/types/analysis";

interface TipsSectionProps {
  categories: CategoryScore[];
}

export function TipsSection({ categories }: TipsSectionProps) {
  // Find the lowest-scoring category as the focus area
  const focus = categories.reduce((low, cat) =>
    cat.score < low.score ? cat : low
  );

  return (
    <div className="space-y-6">
      <Card className="border-primary/30 bg-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-primary">
            Focus Area: {focus.name}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{focus.tip}</p>
        </CardContent>
      </Card>

      <div className="flex justify-center gap-4">
        <Link href="/analyze" className={buttonVariants()}>
          Try Again
        </Link>
      </div>
    </div>
  );
}
