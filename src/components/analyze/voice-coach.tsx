"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

// Voice activity detection threshold (0-255 RMS)
const VAD_THRESHOLD = 30;
const SILENCE_TIMEOUT_MS = 1500;

interface VoiceCoachProps {
  enabled: boolean;
}

export function VoiceCoach({ enabled }: VoiceCoachProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isSendingRef = useRef(false);

  const [active, setActive] = useState(false);
  const [ready, setReady] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [responding, setResponding] = useState(false);

  const playResponseAudio = useCallback((b64Pcm: string) => {
    const pcm = Uint8Array.from(atob(b64Pcm), (c) => c.charCodeAt(0));
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
    setResponding(true);
    audio.onended = () => setResponding(false);
    audio.play().catch(() => setResponding(false));
  }, []);

  const start = useCallback(async () => {
    // Connect voice WebSocket
    const ws = new WebSocket(`${WS_URL}/ws/voice`);
    ws.binaryType = "arraybuffer";

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "ready") {
        setReady(true);
      } else if (msg.type === "audio") {
        playResponseAudio(msg.data);
      } else if (msg.type === "error") {
        console.error("Voice coach:", msg.message);
        setActive(false);
      }
    };

    ws.onclose = () => {
      setActive(false);
      setReady(false);
    };

    wsRef.current = ws;

    // Start microphone with voice activity detection
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true },
    });
    streamRef.current = stream;

    const audioCtx = new AudioContext({ sampleRate: 16000 });
    audioCtxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(stream);
    // ScriptProcessor for raw PCM access + VAD
    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (e) => {
      const input = e.inputBuffer.getChannelData(0);

      // Simple RMS-based voice activity detection
      let sum = 0;
      for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
      const rms = Math.sqrt(sum / input.length) * 255;

      if (rms > VAD_THRESHOLD) {
        setSpeaking(true);
        isSendingRef.current = true;

        // Clear silence timer
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = null;
        }

        // Convert float32 to int16 PCM
        const pcm = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          pcm[i] = Math.max(-32768, Math.min(32767, Math.round(input[i] * 32767)));
        }

        // Send raw PCM bytes to server
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(pcm.buffer);
        }
      } else if (isSendingRef.current) {
        // Start silence timer
        if (!silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            isSendingRef.current = false;
            setSpeaking(false);
            silenceTimerRef.current = null;
          }, SILENCE_TIMEOUT_MS);
        }
        // Keep sending during silence window (captures trailing audio)
        const pcm = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
          pcm[i] = Math.max(-32768, Math.min(32767, Math.round(input[i] * 32767)));
        }
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(pcm.buffer);
        }
      }
    };

    source.connect(processor);
    processor.connect(audioCtx.destination);

    setActive(true);
  }, [playResponseAudio]);

  const stop = useCallback(() => {
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: "end" }));
      } catch { /* ignore */ }
      wsRef.current.close();
      wsRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setActive(false);
    setReady(false);
    setSpeaking(false);
  }, []);

  useEffect(() => {
    return () => { stop(); };
  }, [stop]);

  if (!enabled) return null;

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border p-3">
      <div className="flex-1">
        <p className="text-sm font-medium">
          {!active
            ? "Voice Coach"
            : !ready
            ? "Connecting..."
            : responding
            ? "Coach is speaking..."
            : speaking
            ? "Listening..."
            : "Ask a question about your form"}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {active && (
          <span
            className={`h-3 w-3 rounded-full ${
              speaking ? "bg-red-500" : responding ? "bg-blue-500" : "bg-emerald-500"
            } animate-pulse`}
          />
        )}
        {!active ? (
          <Button size="sm" onClick={start}>
            Start Voice Coach
          </Button>
        ) : (
          <Button size="sm" variant="destructive" onClick={stop}>
            Stop
          </Button>
        )}
      </div>
    </div>
  );
}
