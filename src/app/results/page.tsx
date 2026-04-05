"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Separator } from "@/components/ui/separator";
import { TextAnimate } from "@/components/ui/text-animate";
import { BlurFade } from "@/components/ui/blur-fade";
import { OverallScore } from "@/components/results/overall-score";
import { ScoreBreakdown } from "@/components/results/score-breakdown";
import { TipsSection } from "@/components/results/tips-section";
import { VoiceCoach } from "@/components/analyze/voice-coach";
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
        <p className="text-muted-foreground animate-pulse">Loading results...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-12 space-y-10">
      <div className="text-center space-y-3">
        <TextAnimate
          as="h1"
          by="word"
          animation="blurInUp"
          duration={0.8}
          className="text-3xl sm:text-4xl font-bold"
        >
          Your Form Score
        </TextAnimate>
        <BlurFade delay={0.3} inView>
          <p className="text-muted-foreground">
            Here&apos;s how your three-point shooting form stacks up.
          </p>
        </BlurFade>
      </div>

      <BlurFade delay={0.4} inView>
        <div className="flex flex-col items-center gap-3">
          <OverallScore score={result.overallScore} label={result.overallLabel} />
          {result.mostSimilarPlayer && (
            <p className="text-sm text-muted-foreground">
              Most similar to <span className="font-semibold text-foreground">{result.mostSimilarPlayer.replace(/Shots$/, "").replace(/([A-Z])/g, " $1").trim()}</span>
            </p>
          )}
        </div>
      </BlurFade>

      {(result.coachSummary || result.coaching) && (
        <>
          <Separator className="opacity-30" />
          <BlurFade delay={0.35} inView>
            <div className="rounded-xl border border-border bg-muted/30 p-5 space-y-2">
              <h2 className="text-lg font-semibold">Coach&apos;s Advice</h2>
              {result.coachSummary && (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {result.coachSummary}
                </p>
              )}
              {result.coaching && (
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {typeof result.coaching === "string"
                    ? result.coaching
                    : result.coaching.coaching}
                </p>
              )}
            </div>
          </BlurFade>
        </>
      )}

      <Separator className="opacity-30" />

      <div className="space-y-4">
        <TextAnimate
          as="h2"
          by="word"
          animation="blurInUp"
          startOnView
          once
          className="text-xl font-semibold"
        >
          Breakdown
        </TextAnimate>
        <ScoreBreakdown categories={result.categories} />
      </div>

      <Separator className="opacity-30" />

      <BlurFade delay={0.2} inView>
        <TipsSection categories={result.categories} />
      </BlurFade>


      <Separator className="opacity-30" />

      <BlurFade delay={0.5} inView>
        <VoiceCoach enabled={true} />
      </BlurFade>

      {result.shotCount !== undefined && (
        <BlurFade delay={0.6} inView>
          <p className="text-center text-xs text-muted-foreground">
            Based on {result.shotCount} detected shot{result.shotCount !== 1 ? "s" : ""}
          </p>
        </BlurFade>
      )}
    </div>
  );
}
