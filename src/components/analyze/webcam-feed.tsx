"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { BorderBeam } from "@/components/ui/border-beam";
import { useAccentColor } from "@/components/accent-color-provider";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

interface ShotEvent {
  type: "shot_detected";
  shot_number: number;
  score: number;
  best_ref: string;
  shots_in_batch: number;
  shots_needed: number;
}

interface BatchEvent {
  type: "batch_complete";
  result: Record<string, unknown> & { audio?: string };
}

interface StatusEvent {
  type: "status";
  frame: number;
  tracking: boolean;
  shots_in_batch: number;
}

type ServerMessage = ShotEvent | BatchEvent | StatusEvent;

interface WebcamFeedProps {
  onReady: (ready: boolean) => void;
  onShotDetected?: (event: ShotEvent) => void;
  onBatchComplete?: (result: Record<string, unknown>) => void;
}

function playAudio(b64Audio: string) {
  // Decode base64 PCM to WAV and play
  const pcm = Uint8Array.from(atob(b64Audio), (c) => c.charCodeAt(0));
  const sampleRate = 24000;
  const numChannels = 1;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = pcm.length;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // WAV header
  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
  };
  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);
  new Uint8Array(buffer, 44).set(pcm);

  const blob = new Blob([buffer], { type: "audio/wav" });
  const audio = new Audio(URL.createObjectURL(blob));
  audio.play().catch((e) => console.warn("Audio play failed:", e));
}

export function WebcamFeed({ onReady, onShotDetected, onBatchComplete }: WebcamFeedProps) {
  const { accent } = useAccentColor();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingRef = useRef(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [tracking, setTracking] = useState(false);
  const [shotsInBatch, setShotsInBatch] = useState(0);
  const [lastScore, setLastScore] = useState<number | null>(null);

  const sendFrames = useCallback(() => {
    if (!streamingRef.current || !videoRef.current || !canvasRef.current || !wsRef.current) return;
    if (wsRef.current.readyState !== WebSocket.OPEN) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx || video.videoWidth === 0) {
      requestAnimationFrame(sendFrames);
      return;
    }

    canvas.width = 640;
    canvas.height = Math.round(video.videoHeight * (640 / video.videoWidth));
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          blob.arrayBuffer().then((buf) => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(buf);
            }
          });
        }
        if (streamingRef.current) {
          requestAnimationFrame(sendFrames);
        }
      },
      "image/jpeg",
      0.7
    );
  }, []);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
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

  const startStreaming = useCallback(() => {
    const ws = new WebSocket(`${WS_URL}/ws/analyze`);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      wsRef.current = ws;
      streamingRef.current = true;
      setIsStreaming(true);
      requestAnimationFrame(sendFrames);
    };

    ws.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);
      if (msg.type === "shot_detected") {
        setShotsInBatch(msg.shots_in_batch);
        setLastScore(msg.score);
        onShotDetected?.(msg);
      } else if (msg.type === "batch_complete") {
        setShotsInBatch(0);
        setLastScore(null);
        // Play coaching audio if available
        if (msg.result.audio) {
          playAudio(msg.result.audio as string);
        }
        onBatchComplete?.(msg.result);
      } else if (msg.type === "status") {
        setTracking(msg.tracking);
        setShotsInBatch(msg.shots_in_batch);
      }
    };

    ws.onclose = () => {
      streamingRef.current = false;
      setIsStreaming(false);
      wsRef.current = null;
    };

    ws.onerror = () => {
      setError("Connection to server lost. Is the backend running?");
      streamingRef.current = false;
      setIsStreaming(false);
    };
  }, [sendFrames, onShotDetected, onBatchComplete]);

  const stopStreaming = useCallback(() => {
    streamingRef.current = false;
    setIsStreaming(false);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      streamingRef.current = false;
      if (wsRef.current) wsRef.current.close();
      if (stream) stream.getTracks().forEach((track) => track.stop());
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
            <canvas ref={canvasRef} className="hidden" />
            <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
              <span className={`h-2 w-2 rounded-full ${tracking ? "bg-red-500" : isStreaming ? "bg-emerald-500" : "bg-yellow-500"} animate-pulse`} />
              {tracking ? "Tracking Shot" : isStreaming ? "Analyzing" : "Camera Ready"}
            </div>
            {shotsInBatch > 0 && (
              <div className="absolute top-4 right-4 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
                Shots: {shotsInBatch}/5
                {lastScore !== null && ` | Last: ${lastScore.toFixed(0)}%`}
              </div>
            )}
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

      {stream && (
        <div className="flex justify-center">
          {!isStreaming ? (
            <Button onClick={startStreaming}>Start Analysis</Button>
          ) : (
            <Button onClick={stopStreaming} variant="destructive">Stop Analysis</Button>
          )}
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}
    </div>
  );
}
