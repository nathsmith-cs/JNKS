export interface CategoryScore {
  name: string;
  score: number;
  label: "Excellent" | "Good" | "Needs Work" | "Poor";
  tip: string;
}

export interface WorstJoint {
  joint: string;
  avg_diff_degrees: number;
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
}
