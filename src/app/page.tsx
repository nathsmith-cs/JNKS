import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorks } from "@/components/landing/how-it-works";
import { FeaturesSection } from "@/components/landing/features-section";

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <HowItWorks />
      <FeaturesSection />
    </>
  );
}
