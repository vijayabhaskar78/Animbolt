"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import Sidebar from "@/components/Sidebar";
import VideoPreview from "@/components/VideoPreview";
import CodeEditor from "@/components/CodeEditor";
import SceneTimeline from "@/components/SceneTimeline";
import VoiceoverPanel from "@/components/VoiceoverPanel";
import ExportPanel from "@/components/ExportPanel";
import { getProject } from "@/lib/api";
import { assetUrl } from "@/lib/utils";
import type { TimelineScene } from "@/lib/types";

export default function EditorPage() {
  const params = useParams<{ id: string }>();
  const setProject = useProjectStore((s) => s.setProject);
  const setScenes = useProjectStore((s) => s.setScenes);
  const scenes = useProjectStore((s) => s.scenes);

  useEffect(() => {
    if (!params.id || scenes.length > 0) return;
    void getProject(params.id).then((detail) => {
      setProject(detail.id, detail.title);
      const timeline: TimelineScene[] = detail.scenes
        .sort((a, b) => a.order_index - b.order_index)
        .map((s, idx) => {
          const latest = [...s.versions].sort((a, b) => b.version_no - a.version_no)[0];
          return {
            id: s.id,
            sceneNumber: idx + 1,
            description: latest?.prompt ?? s.title,
            duration: latest?.max_duration_sec ?? 5,
            videoUrl: null,
            thumbnailUrl: s.thumbnail_path ? assetUrl(s.thumbnail_path) : null,
            prompt: latest?.prompt ?? "",
            manimCode: latest?.manim_code ?? "",
            status: latest?.validation_status === "valid" ? "complete" : "idle",
            progress: 0,
          };
        });
      setScenes(timeline);
    }).catch(() => {});
  }, [params.id, scenes.length, setProject, setScenes]);

  return (
    <>
      <Sidebar />
      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          background: "var(--bg)",
        }}
      >
        {/* Main workspace */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* Video preview */}
          <div
            style={{
              flex: 1,
              padding: "12px",
              display: "flex",
              flexDirection: "column",
              minWidth: 0,
            }}
          >
            <VideoPreview />
          </div>

          {/* Code editor */}
          <div
            style={{
              width: "400px",
              flexShrink: 0,
              borderLeft: "1px solid var(--border)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              background: "var(--bg)",
            }}
          >
            <CodeEditor />
          </div>

          {/* Right panel */}
          <div
            style={{
              width: "260px",
              flexShrink: 0,
              borderLeft: "1px solid var(--border)",
              padding: "12px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              overflowY: "auto",
              background: "var(--surface)",
            }}
          >
            <VoiceoverPanel />
            <ExportPanel />
          </div>
        </div>

        {/* Timeline */}
        <SceneTimeline />
      </main>
    </>
  );
}
