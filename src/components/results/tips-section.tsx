"use client";

import Link from "next/link";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { useAccentColor } from "@/components/accent-color-provider";
import type { CategoryScore } from "@/types/analysis";

interface TipsSectionProps {
  categories: CategoryScore[];
}

export function TipsSection({ categories }: TipsSectionProps) {
  const { accent } = useAccentColor();
  const focus = categories.reduce((low, cat) =>
    cat.score < low.score ? cat : low
  );

  return (
    <div className="space-y-6">
      <MagicCard
        className="cursor-default"
        gradientColor={`rgba(${accent.rgb}, 0.1)`}
        gradientFrom={accent.hex}
        gradientTo={accent.hexDark}
      >
        <div className="p-5 space-y-2">
          <h3 className="font-semibold text-primary">
            Focus Area: {focus.name}
          </h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {focus.tip}
          </p>
        </div>
      </MagicCard>

      <div className="flex justify-center">
        <Link href="/analyze">
          <ShimmerButton
            shimmerColor={accent.hex}
            shimmerSize="0.08em"
            background={`rgba(${accent.rgbDark}, 0.85)`}
            borderRadius="12px"
            className="px-8 py-3 text-sm font-semibold"
          >
            Try Again
          </ShimmerButton>
        </Link>
      </div>
    </div>
  );
}
