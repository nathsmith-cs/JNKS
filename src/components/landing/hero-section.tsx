"use client";

import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden py-24 sm:py-32">
      {/* Gradient background */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/10 via-transparent to-amber-600/5" />

      <div className="mx-auto max-w-3xl px-6 text-center space-y-8">
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          Perfect Your{" "}
          <span className="text-primary">Three-Point Shot</span>
        </h1>

        <p className="text-lg text-muted-foreground max-w-xl mx-auto">
          Record your shot or upload a video, and get instant AI-powered
          feedback on your shooting form. Know exactly what to improve.
        </p>

        <div className="flex justify-center gap-4">
          <Link href="/analyze" className={buttonVariants({ size: "lg" })}>
            Start Analyzing
          </Link>
        </div>
      </div>
    </section>
  );
}
