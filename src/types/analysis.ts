export interface CategoryFeedback {
  strengths: string[];
  issues: string[];
  corrections: string[];
}

export interface CategoryScore {
  name: string;
  score: number;
  label: "Excellent" | "Good" | "Needs Work" | "Poor";
  tip: string;
  feedback?: CategoryFeedback | null;
}

export interface WorstJoint {
  joint: string;
  avg_diff_degrees: number;
}

export interface ClipResult {
  clip_index: number;
  time_range: string;
  metrics: Record<string, number>;
  feedback: string;
}

export interface AnalysisResult {
  overallScore: number;
  overallLabel: "Excellent" | "Good" | "Needs Work" | "Poor";
  categories: CategoryScore[];
  worstJoints?: WorstJoint[];
  timestamp: string;
  inputType: "webcam" | "upload";
  shotCount?: number;
  coaching?: string;
  coachSummary?: string | null;
  clips?: ClipResult[] | null;
}
