"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TextAnimate } from "@/components/ui/text-animate";
import { BlurFade } from "@/components/ui/blur-fade";
import { WebcamFeed } from "@/components/analyze/webcam-feed";
import { VideoUpload } from "@/components/analyze/video-upload";
import { AnalyzeButton } from "@/components/analyze/analyze-button";

export default function AnalyzePage() {
  const router = useRouter();
  const [webcamReady, setWebcamReady] = useState(false);
  const [uploadReady, setUploadReady] = useState(false);
  const [activeTab, setActiveTab] = useState("webcam");
  const [videoFile, setVideoFile] = useState<File | null>(null);

  const handleBatchComplete = useCallback(
    (result: Record<string, unknown>) => {
      sessionStorage.setItem("analysisResult", JSON.stringify(result));
      router.push("/results");
    },
    [router]
  );

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
            <TabsTrigger value="webcam">Live Camera</TabsTrigger>
            <TabsTrigger value="upload">Upload Video</TabsTrigger>
          </TabsList>

          <TabsContent value="webcam" className="space-y-6">
            <WebcamFeed
              onReady={setWebcamReady}
              onBatchComplete={handleBatchComplete}
            />
          </TabsContent>

          <TabsContent value="upload" className="space-y-6">
            <VideoUpload
              onReady={setUploadReady}
              onFileSelected={setVideoFile}
            />
            <AnalyzeButton disabled={!uploadReady} inputType="upload" videoFile={videoFile} />
          </TabsContent>
        </Tabs>
      </BlurFade>
    </div>
  );
}
