export interface CategoryScore {
  name: string;
  score: number;
  label: "Excellent" | "Good" | "Needs Work" | "Poor";
  tip: string;
}

export interface AnalysisResult {
  overallScore: number;
  overallLabel: "Excellent" | "Good" | "Needs Work" | "Poor";
  categories: CategoryScore[];
  timestamp: string;
  inputType: "webcam" | "upload";
}
