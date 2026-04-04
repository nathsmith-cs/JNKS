"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Separator } from "@/components/ui/separator";
import { OverallScore } from "@/components/results/overall-score";
import { ScoreBreakdown } from "@/components/results/score-breakdown";
import { TipsSection } from "@/components/results/tips-section";
import type { AnalysisResult } from "@/types/analysis";

export default function ResultsPage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("analysisResult");
    if (!stored) {
      router.push("/analyze");
      return;
    }
    setResult(JSON.parse(stored));
  }, [router]);

  if (!result) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-muted-foreground">Loading results...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-12 space-y-10">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold">Your Form Score</h1>
        <p className="text-muted-foreground">
          Here&apos;s how your three-point shooting form stacks up.
        </p>
      </div>

      <div className="flex justify-center">
        <OverallScore
          score={result.overallScore}
          label={result.overallLabel}
        />
      </div>

      <Separator />

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Breakdown</h2>
        <ScoreBreakdown categories={result.categories} />
      </div>

      <Separator />

      <TipsSection categories={result.categories} />
    </div>
  );
}
