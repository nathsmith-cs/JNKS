"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { TextAnimate } from "@/components/ui/text-animate";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { BlurFade } from "@/components/ui/blur-fade";
import { useAccentColor } from "@/components/accent-color-provider";


const BasketballScene = dynamic(
  () => import("@/components/3d/basketball-scene"),
  { ssr: false, loading: () => null }
);

export function HeroSection() {
  const { accent } = useAccentColor();

  return (
    <section className="relative py-12 sm:py-20">
      <div className="mx-auto max-w-6xl px-6">
        <div className="flex flex-col lg:flex-row items-center gap-8 lg:gap-12">
          {/* Left side — Basketball + effects + text */}
          <div className="flex-1 text-center lg:text-left space-y-6">
            {/* Basketball with CSS glow */}
            <div className="relative mx-auto lg:mx-0 h-[280px] w-[280px] sm:h-[350px] sm:w-[350px]">
              {/* Ambient glow */}
              <div className="absolute inset-0 -inset-x-16 -inset-y-16 rounded-full blur-3xl" style={{ backgroundColor: `rgba(${accent.rgb}, 0.1)` }} />
              <div className="absolute inset-0 -inset-x-8 -inset-y-8 rounded-full blur-2xl" style={{ backgroundColor: `rgba(${accent.rgbDark}, 0.05)` }} />
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
              className="text-5xl font-bold tracking-tight sm:text-7xl font-heading"
            >
              Perfect Your Three-Point Shot
            </TextAnimate>

            <BlurFade delay={0.4} inView>
              <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto lg:mx-0 leading-relaxed">
                Record your shot or upload a video, and get instant AI-powered
                feedback on your shooting form. Know exactly what to improve.
              </p>
            </BlurFade>

            <BlurFade delay={0.6} inView>
              <div className="flex justify-center lg:justify-start">
                <Link href="/analyze">
                  <ShimmerButton
                    shimmerColor={accent.hex}
                    shimmerSize="0.08em"
                    background={`rgba(${accent.rgbDark}, 0.85)`}
                    borderRadius="12px"
                    className="px-8 py-4 text-base font-semibold"
                  >
                    Start Analyzing
                  </ShimmerButton>
                </Link>
              </div>
            </BlurFade>
          </div>

          {/* Right side — Wireframe video */}
          <BlurFade delay={0.3} inView>
            <div className="flex-1 flex justify-center lg:justify-end">
              <div className="relative w-[260px] sm:w-[300px] lg:w-[340px] rounded-2xl overflow-hidden border border-white/10" style={{ boxShadow: `0 25px 50px -12px rgba(${accent.rgb}, 0.1)` }}>
                <video
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full h-auto"
                >
                  <source src="/wireframe-hero.mp4" type="video/mp4" />
                </video>
              </div>
            </div>
          </BlurFade>
        </div>
      </div>
    </section>
  );
}
