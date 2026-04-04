"use client";

import { useState, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TextAnimate } from "@/components/ui/text-animate";
import { BlurFade } from "@/components/ui/blur-fade";
import { WebcamFeed } from "@/components/analyze/webcam-feed";
import { VideoUpload } from "@/components/analyze/video-upload";
import { AnalyzeButton } from "@/components/analyze/analyze-button";

export default function AnalyzePage() {
  const [webcamReady, setWebcamReady] = useState(false);
  const [uploadReady, setUploadReady] = useState(false);
  const [activeTab, setActiveTab] = useState("webcam");

  // Store the video data from each input method
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const getWebcamBlob = useCallback(() => recordedBlob, [recordedBlob]);
  const getUploadBlob = useCallback(() => uploadFile, [uploadFile]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 space-y-8">
      <div className="text-center space-y-3">
        <TextAnimate
          as="h1"
          by="word"
          animation="blurInUp"
          duration={0.8}
          className="text-3xl sm:text-4xl font-bold"
        >
          Analyze Your Shot
        </TextAnimate>
        <BlurFade delay={0.3} inView>
          <p className="text-muted-foreground">
            Use your camera for live analysis or upload a video of your
            three-point shot.
          </p>
        </BlurFade>
      </div>

      <BlurFade delay={0.4} inView>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="webcam">Webcam</TabsTrigger>
            <TabsTrigger value="upload">Upload Video</TabsTrigger>
          </TabsList>

          <TabsContent value="webcam" className="space-y-6">
            <WebcamFeed
              onReady={setWebcamReady}
              onRecorded={setRecordedBlob}
            />
            <AnalyzeButton
              disabled={!webcamReady}
              inputType="webcam"
              getVideoBlob={getWebcamBlob}
            />
          </TabsContent>

          <TabsContent value="upload" className="space-y-6">
            <VideoUpload
              onReady={setUploadReady}
              onFileSelected={setUploadFile}
            />
            <AnalyzeButton
              disabled={!uploadReady}
              inputType="upload"
              getVideoBlob={getUploadBlob}
            />
          </TabsContent>
        </Tabs>
      </BlurFade>
    </div>
  );
}
