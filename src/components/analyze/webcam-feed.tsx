"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { BorderBeam } from "@/components/ui/border-beam";
import { useAccentColor } from "@/components/accent-color-provider";

interface WebcamFeedProps {
  onReady: (ready: boolean) => void;
  onRecorded: (blob: Blob | null) => void;
}

export function WebcamFeed({ onReady, onRecorded }: WebcamFeedProps) {
  const { accent } = useAccentColor();
  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [hasRecording, setHasRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch {
      setError("Could not access camera. Please allow camera permissions.");
    }
  }, []);

  const startRecording = useCallback(() => {
    if (!stream) return;

    chunksRef.current = [];
    setHasRecording(false);
    onRecorded(null);
    onReady(false);

    // Pick a MIME type the browser supports
    const mimeType = ["video/webm;codecs=vp9", "video/webm", "video/mp4"].find(
      (t) => MediaRecorder.isTypeSupported(t)
    );

    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, {
        type: mimeType || "video/webm",
      });
      onRecorded(blob);
      onReady(true);
      setHasRecording(true);
    };

    recorder.start();
    setIsRecording(true);
    setElapsed(0);

    timerRef.current = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);
  }, [stream, onRecorded, onReady]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reRecord = useCallback(() => {
    setHasRecording(false);
    onRecorded(null);
    onReady(false);
    startRecording();
  }, [startRecording, onRecorded, onReady]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [stream]);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="space-y-4">
      <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-border/50 bg-muted/20">
        {stream ? (
          <>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="h-full w-full object-cover"
            />
            {/* Status badge: top-left */}
            <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
              {isRecording ? (
                <>
                  <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                  Recording {formatTime(elapsed)}
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  Live
                </>
              )}
            </div>
            <BorderBeam
              size={120}
              duration={8}
              colorFrom={accent.hex}
              colorTo={accent.hexDark}
              borderWidth={2}
            />
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-muted-foreground/60"
            >
              <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
              <circle cx="12" cy="13" r="3" />
            </svg>
            <p className="text-sm text-muted-foreground text-center">
              Click below to start your camera and begin analyzing your shot.
            </p>
            <Button onClick={startCamera} className="mt-2">
              Start Camera
            </Button>
          </div>
        )}
      </div>

      {/* Recording controls — only show after camera is on */}
      {stream && (
        <div className="flex justify-center gap-3">
          {isRecording ? (
            <Button variant="destructive" onClick={stopRecording}>
              Stop Recording
            </Button>
          ) : hasRecording ? (
            <Button variant="outline" onClick={reRecord}>
              Re-record
            </Button>
          ) : (
            <Button onClick={startRecording}>Record</Button>
          )}
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}
    </div>
  );
}
