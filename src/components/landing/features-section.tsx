"use client";

import { MagicCard } from "@/components/ui/magic-card";
import { BlurFade } from "@/components/ui/blur-fade";
import { TextAnimate } from "@/components/ui/text-animate";

const features = [
  {
    title: "Real-Time Webcam Analysis",
    description:
      "Get instant feedback using your device camera — no uploads needed.",
  },
  {
    title: "Video Upload Support",
    description: "Already have footage? Upload any video file for analysis.",
  },
  {
    title: "Detailed Form Breakdown",
    description:
      "Scores for elbow angle, follow-through, release point, and stance.",
  },
  {
    title: "Personalized Tips",
    description: "Actionable advice tailored to your weakest areas.",
  },
];

export function FeaturesSection() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-5xl px-6 space-y-12">
        <TextAnimate
          as="h2"
          by="word"
          animation="blurInUp"
          startOnView
          once
          className="text-3xl font-bold text-center"
        >
          Features
        </TextAnimate>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {features.map((feature, i) => (
            <BlurFade key={feature.title} delay={0.1 * i} inView>
              <MagicCard
                className="h-full cursor-default"
                gradientColor="rgba(249, 115, 22, 0.06)"
                gradientFrom="#f97316"
                gradientTo="#ea580c"
              >
                <div className="p-6 space-y-2">
                  <h3 className="font-semibold text-lg">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </MagicCard>
            </BlurFade>
          ))}
        </div>
      </div>
    </section>
  );
}
