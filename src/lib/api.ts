import type { AnalysisResult } from "@/types/analysis";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function analyzeVideo(
  file: Blob,
  inputType: "webcam" | "upload"
): Promise<AnalysisResult> {
  const formData = new FormData();
  const extension = inputType === "webcam" ? "webm" : "mp4";
  formData.append("file", file, `shot.${extension}`);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      const message =
        body?.detail || `Analysis failed (status ${res.status})`;
      throw new Error(message);
    }

    return (await res.json()) as AnalysisResult;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Analysis took too long. Try a shorter clip.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}
