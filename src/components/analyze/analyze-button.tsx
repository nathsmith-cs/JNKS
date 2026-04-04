"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { generateMockAnalysis } from "@/lib/mock-data";

interface AnalyzeButtonProps {
  disabled: boolean;
  inputType: "webcam" | "upload";
}

export function AnalyzeButton({ disabled, inputType }: AnalyzeButtonProps) {
  const router = useRouter();
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleAnalyze = () => {
    setIsAnalyzing(true);

    // Simulate analysis time
    setTimeout(() => {
      const result = generateMockAnalysis(inputType);
      sessionStorage.setItem("analysisResult", JSON.stringify(result));
      router.push("/results");
    }, 2500);
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <Button
        size="lg"
        onClick={handleAnalyze}
        disabled={disabled || isAnalyzing}
        className="w-full max-w-xs"
      >
        {isAnalyzing ? (
          <span className="flex items-center gap-2">
            <svg
              className="h-4 w-4 animate-spin"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Analyzing your form...
          </span>
        ) : (
          "Analyze My Form"
        )}
      </Button>
      {isAnalyzing && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Comparing your shot to ideal form...
        </p>
      )}
    </div>
  );
}
