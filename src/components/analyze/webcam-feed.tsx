"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { BorderBeam } from "@/components/ui/border-beam";
import { useAccentColor } from "@/components/accent-color-provider";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const CHUNK_INTERVAL_MS = 1500; // 1.5-second video chunks

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
  const pcm = Uint8Array.from(atob(b64Audio), (c) => c.charCodeAt(0));
  const sampleRate = 24000;
  const buffer = new ArrayBuffer(44 + pcm.length);
  const view = new DataView(buffer);
  const writeStr = (o: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i));
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + pcm.length, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, pcm.length, true);
  new Uint8Array(buffer, 44).set(pcm);
  const blob = new Blob([buffer], { type: "audio/wav" });
  const audio = new Audio(URL.createObjectURL(blob));
  audio.play().catch((e) => console.warn("Audio play failed:", e));
}

export function WebcamFeed({ onReady, onShotDetected, onBatchComplete }: WebcamFeedProps) {
  const { accent } = useAccentColor();
  const videoRef = useRef<HTMLVideoElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const streamingRef = useRef(false);
  const [tracking, setTracking] = useState(false);
  const [shotsInBatch, setShotsInBatch] = useState(0);
  const [lastScore, setLastScore] = useState<number | null>(null);

  const startCamera = useCallback(async () => {
    try {
      setError(null);
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      onReady(true);
    } catch {
      setError("Could not access camera. Please allow camera permissions.");
      onReady(false);
    }
  }, [onReady]);

  const startStreaming = useCallback(() => {
    if (!stream) return;

    // Connect WebSocket
    const ws = new WebSocket(`${WS_URL}/ws/analyze`);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      wsRef.current = ws;
      streamingRef.current = true;
      setIsStreaming(true);

      // Record complete video files in a stop/start cycle
      // Each chunk is a full valid file with headers
      const mimeType = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm", "video/mp4"].find(
        (t) => MediaRecorder.isTypeSupported(t)
      );

      const startRecordingCycle = () => {
        if (!streamingRef.current || ws.readyState !== WebSocket.OPEN) return;

        const chunks: Blob[] = [];
        const recorder = new MediaRecorder(stream, {
          mimeType: mimeType || undefined,
          videoBitsPerSecond: 4_000_000,
        });

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunks.push(e.data);
        };

        recorder.onstop = () => {
          if (chunks.length > 0 && ws.readyState === WebSocket.OPEN) {
            const blob = new Blob(chunks, { type: mimeType || "video/webm" });
            blob.arrayBuffer().then((buf) => {
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(buf);
              }
            });
          }
          // Start next cycle
          if (streamingRef.current) {
            startRecordingCycle();
          }
        };

        recorder.start();
        recorderRef.current = recorder;

        // Stop after CHUNK_INTERVAL_MS to produce a complete file
        setTimeout(() => {
          if (recorder.state === "recording") {
            recorder.stop();
          }
        }, CHUNK_INTERVAL_MS);
      };

      startRecordingCycle();
    };

    ws.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data);
      if (msg.type === "shot_detected") {
        setShotsInBatch(msg.shots_in_batch);
        setLastScore(msg.score);
        onShotDetected?.(msg);
      } else if (msg.type === "batch_complete") {
        // Stop recording immediately — batch is done
        streamingRef.current = false;
        if (recorderRef.current && recorderRef.current.state === "recording") {
          recorderRef.current.stop();
        }
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        setIsStreaming(false);
        setShotsInBatch(0);
        setLastScore(null);
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
      if (recorderRef.current && recorderRef.current.state === "recording") {
        recorderRef.current.stop();
      }
    };

    ws.onerror = () => {
      setError("Connection to server lost. Is the backend running?");
      streamingRef.current = false;
      setIsStreaming(false);
    };
  }, [stream, onShotDetected, onBatchComplete]);

  // Auto-start streaming when camera is ready
  useEffect(() => {
    if (stream && !isStreaming) {
      const t = setTimeout(() => startStreaming(), 500);
      return () => clearTimeout(t);
    }
  }, [stream, isStreaming, startStreaming]);

  // Ensure video element always has the stream
  useEffect(() => {
    if (stream && videoRef.current && !videoRef.current.srcObject) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Cleanup
  useEffect(() => {
    return () => {
      streamingRef.current = false;
      if (recorderRef.current && recorderRef.current.state === "recording") {
        recorderRef.current.stop();
      }
      if (wsRef.current) wsRef.current.close();
      if (stream) stream.getTracks().forEach((track) => track.stop());
    };
  }, [stream]);

  return (
    <div className="space-y-4">
      <div className="relative w-full aspect-[9/16] max-w-sm mx-auto overflow-hidden rounded-2xl border border-border/50 bg-muted/20">
        {stream ? (
          <>
            <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-contain" />
            <div className="absolute top-4 left-4 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
              <span className={`h-2 w-2 rounded-full ${tracking ? "bg-red-500" : isStreaming ? "bg-emerald-500" : "bg-yellow-500"} animate-pulse`} />
              {tracking ? "Tracking Shot" : isStreaming ? "Analyzing" : "Camera Ready"}
            </div>
            {shotsInBatch > 0 && (
              <div className="absolute top-4 right-4 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
                Shots: {shotsInBatch}/{SHOTS_PER_BATCH}
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

      {error && (
        <p className="text-sm text-destructive text-center">{error}</p>
      )}
    </div>
  );
}

const SHOTS_PER_BATCH = 5;
