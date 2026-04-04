"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { TextAnimate } from "@/components/ui/text-animate";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { BlurFade } from "@/components/ui/blur-fade";


const BasketballScene = dynamic(
  () => import("@/components/3d/basketball-scene"),
  { ssr: false }
);

export function HeroSection() {
  return (
    <section className="relative py-12 sm:py-20">
      <div className="mx-auto max-w-4xl px-6 text-center space-y-6">
        {/* Basketball with CSS glow */}
        <div className="relative mx-auto h-[350px] w-[350px] sm:h-[450px] sm:w-[450px]">
          {/* Ambient glow — lives behind the canvas, bleeds freely */}
          <div className="absolute inset-0 -inset-x-16 -inset-y-16 rounded-full bg-orange-500/10 blur-3xl" />
          <div className="absolute inset-0 -inset-x-8 -inset-y-8 rounded-full bg-orange-600/5 blur-2xl" />
          {/* 3D canvas */}
          <div className="relative h-full w-full">
            <BasketballScene />
          </div>
        </div>

        <TextAnimate
          as="h1"
          by="word"
          animation="blurInUp"
          duration={1}
          className="text-5xl font-bold tracking-tight sm:text-7xl"
        >
          Perfect Your Three-Point Shot
        </TextAnimate>

        <BlurFade delay={0.4} inView>
          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Record your shot or upload a video, and get instant AI-powered
            feedback on your shooting form. Know exactly what to improve.
          </p>
        </BlurFade>

        <BlurFade delay={0.6} inView>
          <div className="flex justify-center">
            <Link href="/analyze">
              <ShimmerButton
                shimmerColor="#f97316"
                shimmerSize="0.08em"
                background="rgba(234, 88, 12, 0.85)"
                borderRadius="12px"
                className="px-8 py-4 text-base font-semibold"
              >
                Start Analyzing
              </ShimmerButton>
            </Link>
          </div>
        </BlurFade>
      </div>
    </section>
  );
}
