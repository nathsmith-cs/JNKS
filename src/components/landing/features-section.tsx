import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    title: "Real-Time Webcam Analysis",
    description: "Get instant feedback using your device camera — no uploads needed.",
  },
  {
    title: "Video Upload Support",
    description: "Already have footage? Upload any video file for analysis.",
  },
  {
    title: "Detailed Form Breakdown",
    description: "Scores for elbow angle, follow-through, release point, and stance.",
  },
  {
    title: "Personalized Tips",
    description: "Actionable advice tailored to your weakest areas.",
  },
];

export function FeaturesSection() {
  return (
    <section className="py-16 bg-muted/30">
      <div className="mx-auto max-w-4xl px-6 space-y-10">
        <h2 className="text-2xl font-bold text-center">Features</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {features.map((feature) => (
            <Card key={feature.title}>
              <CardContent className="pt-6 space-y-2">
                <h3 className="font-semibold">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
