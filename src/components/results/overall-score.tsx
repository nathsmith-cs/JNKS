"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { NumberTicker } from "@/components/ui/number-ticker";
import { BorderBeam } from "@/components/ui/border-beam";

interface OverallScoreProps {
  score: number;
  label: string;
}

export function OverallScore({ score, label }: OverallScoreProps) {
  const [displayed, setDisplayed] = useState(0);

  // Animate the SVG ring
  useEffect(() => {
    const duration = 1200;
    const startTime = performance.now();

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - (1 - progress) * (1 - progress);
      setDisplayed(Math.round(eased * score));
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }, [score]);

  const size = 220;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - displayed / 100);

  const color =
    score >= 80
      ? "text-emerald-500"
      : score >= 60
        ? "text-amber-500"
        : "text-red-500";

  const strokeColor =
    score >= 80
      ? "stroke-emerald-500"
      : score >= 60
        ? "stroke-amber-500"
        : "stroke-red-500";

  const beamFrom =
    score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";
  const beamTo =
    score >= 80 ? "#059669" : score >= 60 ? "#d97706" : "#dc2626";

  return (
    <div className="flex flex-col items-center gap-5">
      <div className="relative rounded-full p-1">
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-muted/30"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={`${strokeColor} transition-all duration-100`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <NumberTicker
            value={score}
            delay={0.2}
            className={`text-5xl font-bold tabular-nums ${color}`}
          />
          <span className="text-sm text-muted-foreground mt-1">/ 100</span>
        </div>
        <BorderBeam
          size={80}
          duration={6}
          colorFrom={beamFrom}
          colorTo={beamTo}
          borderWidth={2}
        />
      </div>
      <Badge variant="secondary" className="text-sm px-4 py-1.5">
        {label}
      </Badge>
    </div>
  );
}
