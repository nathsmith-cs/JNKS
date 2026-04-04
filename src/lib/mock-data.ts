import type { AnalysisResult, CategoryScore } from "@/types/analysis";

function getLabel(score: number): CategoryScore["label"] {
  if (score >= 90) return "Excellent";
  if (score >= 75) return "Good";
  if (score >= 60) return "Needs Work";
  return "Poor";
}

// Random integer between min and max (inclusive)
function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Pick a random item from an array
function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

const tipsByCategory: Record<string, string[]> = {
  "Elbow Angle": [
    "Keep your elbow at 90° at the set point for a consistent release.",
    "Your elbow is drifting outward — tuck it under the ball.",
    "Great elbow alignment — maintain that L-shape on every shot.",
  ],
  "Follow-Through": [
    "Extend your wrist fully and hold — reach into the cookie jar.",
    "Your follow-through is cutting short — snap the wrist and freeze.",
    "Solid follow-through — keep that relaxed wrist flick.",
  ],
  "Release Point": [
    "Release at the peak of your jump for maximum arc.",
    "You're releasing too early — wait until you reach the top.",
    "Great timing on the release — that high arc gives you a shooter's touch.",
  ],
  "Stance": [
    "Feet shoulder-width apart with your shooting foot slightly ahead.",
    "Widen your base a bit — you're losing balance on the release.",
    "Strong foundation — your lower body is set up well for power.",
  ],
};

const weights: Record<string, number> = {
  "Elbow Angle": 0.3,
  "Follow-Through": 0.25,
  "Release Point": 0.25,
  "Stance": 0.2,
};

export function generateMockAnalysis(
  inputType: "webcam" | "upload"
): AnalysisResult {
  const categoryNames = ["Elbow Angle", "Follow-Through", "Release Point", "Stance"];

  const categories: CategoryScore[] = categoryNames.map((name) => {
    const score = randInt(60, 95);
    return {
      name,
      score,
      label: getLabel(score),
      tip: pick(tipsByCategory[name]),
    };
  });

  // Weighted average for overall score
  const overallScore = Math.round(
    categories.reduce((sum, cat) => sum + cat.score * weights[cat.name], 0)
  );

  return {
    overallScore,
    overallLabel: getLabel(overallScore),
    categories,
    timestamp: new Date().toISOString(),
    inputType,
  };
}
