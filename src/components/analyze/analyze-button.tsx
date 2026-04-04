"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AnalyzeButtonProps {
  disabled: boolean;
  inputType: "webcam" | "upload";
  videoFile?: File | null;
}

export function AnalyzeButton({ disabled, inputType, videoFile }: AnalyzeButtonProps) {
  const router = useRouter();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [status, setStatus] = useState("");

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setStatus("Uploading video...");

    try {
      let file: File;

      if (inputType === "upload" && videoFile) {
        file = videoFile;
      } else {
        setStatus("No video available");
        setIsAnalyzing(false);
        return;
      }

      setStatus("Analyzing your form...");

      const formData = new FormData();
      formData.append("video", file);

      const res = await fetch(
        `${API_URL}/api/analyze?reference=StephCurryShots&input_type=${inputType}`,
        { method: "POST", body: formData }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Analysis failed");
      }

      const result = await res.json();
      sessionStorage.setItem("analysisResult", JSON.stringify(result));
      router.push("/results");
    } catch (err) {
      setStatus(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
      setTimeout(() => {
        setIsAnalyzing(false);
        setStatus("");
      }, 3000);
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
            {status || "Analyzing..."}
          </span>
        ) : (
          "Analyze My Form"
        )}
      </Button>
      {isAnalyzing && (
        <p className="text-xs text-muted-foreground animate-pulse">
          Comparing your shot to Steph Curry&apos;s form...
        </p>
      )}
    </div>
  );
}
