"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { analyzeVideo } from "@/lib/api";

interface AnalyzeButtonProps {
  disabled: boolean;
  inputType: "webcam" | "upload";
  getVideoBlob: () => Blob | null;
}

export function AnalyzeButton({
  disabled,
  inputType,
  getVideoBlob,
}: AnalyzeButtonProps) {
  const router = useRouter();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setError(null);
    const blob = getVideoBlob();
    if (!blob) {
      setError("No video to analyze. Please record or upload a video first.");
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await analyzeVideo(blob, inputType);
      sessionStorage.setItem("analysisResult", JSON.stringify(result));
      router.push("/results");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Something went wrong."
      );
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <Button
        size="lg"
        onClick={handleAnalyze}
        disabled={disabled || isAnalyzing}
        className="w-full max-w-xs px-6 py-3 text-sm font-semibold"
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
      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}
    </div>
  );
}
