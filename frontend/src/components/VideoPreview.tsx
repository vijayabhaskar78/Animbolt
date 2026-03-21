"use client";

import { useEffect, useRef, useState } from "react";
import { useProjectStore } from "@/store/useProjectStore";
import { apiBase } from "@/lib/api";
import { assetUrl, toWsBase } from "@/lib/utils";

const STEP_LABELS: Record<string, string> = {
  generating_code: "Writing Manim code…",
  rendering_video: "Rendering preview…",
};

interface Props {
  forceLoading?: boolean;
}

export default function VideoPreview({ forceLoading }: Props) {
  const previewUrl = useProjectStore((s) => s.previewUrl);
  const selectedSceneId = useProjectStore((s) => s.selectedSceneId);
  const scenes = useProjectStore((s) => s.scenes);
  const activeJobs = useProjectStore((s) => s.activeJobs);

  const [streamFrame, setStreamFrame] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const selectedScene = scenes.find((s) => s.id === selectedSceneId);

  const runningJobId = Object.entries(activeJobs).find(
    ([, v]) => v.status === "running"
  )?.[0];

  useEffect(() => {
    if (!runningJobId) {
      if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
      setStreamFrame(null);
      return;
    }
    const ws = new WebSocket(`${toWsBase(apiBase)}/ws/preview/${runningJobId}`);
    wsRef.current = ws;
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data as string);
        if (msg.payload_base64) setStreamFrame(`data:image/png;base64,${msg.payload_base64}`);
      } catch { /* heartbeat */ }
    };
    ws.onclose = () => { wsRef.current = null; };
    return () => { ws.close(); };
  }, [runningJobId]);

  const videoSrc = selectedScene?.videoUrl
    ? assetUrl(selectedScene.videoUrl)
    : previewUrl
    ? assetUrl(previewUrl)
    : null;

  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        background: "#000",
        borderRadius: "12px",
        overflow: "hidden",
        border: "1px solid var(--border)",
      }}
    >
      {/* Screen */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          background: "radial-gradient(ellipse at center, #0C0C0E 0%, #000 100%)",
        }}
      >
        {streamFrame ? (
          <img
            src={streamFrame}
            alt="Live preview"
            style={{ width: "100%", maxHeight: "100%", objectFit: "contain", display: "block" }}
          />
        ) : videoSrc ? (
          <video
            key={videoSrc}
            controls
            autoPlay
            style={{ width: "100%", maxHeight: "100%", display: "block", borderRadius: "4px" }}
            src={videoSrc}
          />
        ) : selectedScene && (selectedScene.status === "generating_code" || selectedScene.status === "rendering_video") ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "20px",
              color: "var(--text-3)",
              padding: "20px",
              width: "100%",
            }}
          >
            {/* Multi-ring loader */}
            <div style={{ position: "relative", width: "72px", height: "72px" }}>
              {/* Outer ring */}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: "50%",
                  border: "2px solid var(--border)",
                  borderTopColor: "var(--amber)",
                  borderRightColor: "var(--amber)",
                  animation: "spin 1.1s cubic-bezier(0.6,0,0.4,1) infinite",
                  boxShadow: "0 0 16px rgba(245,158,11,0.25)",
                }}
              />
              {/* Middle ring */}
              <div
                style={{
                  position: "absolute",
                  inset: "12px",
                  borderRadius: "50%",
                  border: "2px solid var(--border)",
                  borderTopColor: "rgba(245,158,11,0.45)",
                  animation: "spinReverse 0.8s linear infinite",
                }}
              />
              {/* Center dot */}
              <div
                style={{
                  position: "absolute",
                  inset: "28px",
                  borderRadius: "50%",
                  background: "var(--amber)",
                  animation: "pulse 1.4s ease-in-out infinite",
                  boxShadow: "0 0 8px rgba(245,158,11,0.6)",
                }}
              />
            </div>

            <div style={{ textAlign: "center" }}>
              <p style={{ fontSize: "14px", margin: 0, marginBottom: "6px", color: "var(--text-2)", fontWeight: 500, letterSpacing: "0.01em" }}>
                {STEP_LABELS[selectedScene.status] ?? "Processing…"}
              </p>
              {/* Scene number label — DISABLED */}
            </div>
            <div style={{ width: "100%", maxWidth: "280px" }}>
              <div className="progress-track">
                {selectedScene.progress > 0 ? (
                  <div className="progress-fill" style={{ width: `${selectedScene.progress}%`, transition: "width 0.5s ease" }} />
                ) : (
                  <div className="progress-fill progress-fill-indeterminate" />
                )}
              </div>
            </div>
          </div>
        ) : forceLoading ? (
          /* Project loading or auto-start pending: show spinner, no text */
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "100%",
              height: "100%",
            }}
          >
            <div style={{ position: "relative", width: "72px", height: "72px" }}>
              <div style={{
                position: "absolute", inset: 0, borderRadius: "50%",
                border: "2px solid var(--border)", borderTopColor: "var(--amber)", borderRightColor: "var(--amber)",
                animation: "spin 1.1s cubic-bezier(0.6,0,0.4,1) infinite",
                boxShadow: "0 0 16px rgba(245,158,11,0.25)",
              }} />
              <div style={{
                position: "absolute", inset: "12px", borderRadius: "50%",
                border: "2px solid var(--border)", borderTopColor: "rgba(245,158,11,0.45)",
                animation: "spinReverse 0.8s linear infinite",
              }} />
              <div style={{
                position: "absolute", inset: "28px", borderRadius: "50%",
                background: "var(--amber)",
                animation: "pulse 1.4s ease-in-out infinite",
                boxShadow: "0 0 8px rgba(245,158,11,0.6)",
              }} />
            </div>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
              color: "var(--text-3)",
            }}
          >
            <div
              style={{
                width: "64px",
                height: "64px",
                borderRadius: "50%",
                border: "1px solid var(--border-mid)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "28px",
              }}
            >
              ▷
            </div>
            <p style={{ fontSize: "14px", margin: 0, textAlign: "center", lineHeight: 1.5 }}>
              Generate a scene to<br />preview it here
            </p>
          </div>
        )}

        {/* Streaming overlay */}
        {runningJobId && (
          <div
            style={{
              position: "absolute",
              top: "10px",
              right: "10px",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "rgba(9,9,10,0.75)",
              backdropFilter: "blur(6px)",
              border: "1px solid var(--border-mid)",
              borderRadius: "999px",
              padding: "4px 10px",
            }}
          >
            <div
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "var(--amber)",
                animation: "pulse 1s ease-in-out infinite",
              }}
            />
            <span style={{ fontSize: "10px", color: "var(--amber)", fontWeight: 600, letterSpacing: "0.06em" }}>
              LIVE
            </span>
          </div>
        )}
      </div>

      {/* Info bar — scene label DISABLED, duration kept */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          padding: "7px 12px",
          borderTop: "1px solid var(--border)",
          background: "var(--surface)",
        }}
      >
        {selectedScene?.duration && (
          <span style={{ fontSize: "11px", color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>
            {selectedScene.duration}s
          </span>
        )}
      </div>
    </div>
  );
}
