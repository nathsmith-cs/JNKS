"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WebcamFeed } from "@/components/analyze/webcam-feed";
import { VideoUpload } from "@/components/analyze/video-upload";
import { AnalyzeButton } from "@/components/analyze/analyze-button";

export default function AnalyzePage() {
  const [webcamReady, setWebcamReady] = useState(false);
  const [uploadReady, setUploadReady] = useState(false);
  const [activeTab, setActiveTab] = useState("webcam");

  return (
    <div className="mx-auto max-w-2xl px-6 py-12 space-y-8">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold">Analyze Your Shot</h1>
        <p className="text-muted-foreground">
          Use your camera for live analysis or upload a video of your
          three-point shot.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="webcam">Webcam</TabsTrigger>
          <TabsTrigger value="upload">Upload Video</TabsTrigger>
        </TabsList>

        <TabsContent value="webcam" className="space-y-6">
          <WebcamFeed onReady={setWebcamReady} />
          <AnalyzeButton disabled={!webcamReady} inputType="webcam" />
        </TabsContent>

        <TabsContent value="upload" className="space-y-6">
          <VideoUpload onReady={setUploadReady} />
          <AnalyzeButton disabled={!uploadReady} inputType="upload" />
        </TabsContent>
      </Tabs>
    </div>
  );
}
