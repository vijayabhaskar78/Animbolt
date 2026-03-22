"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import Sidebar from "@/components/Sidebar";
import PromptInput from "@/components/PromptInput";
import VideoPreview from "@/components/VideoPreview";
import { addChatMessage, generateScene, getChatMessages, getJob, getProject, regenerateScene, refineScene, renderHD } from "@/lib/api";
import { assetUrl } from "@/lib/utils";
import type { TimelineScene } from "@/lib/types";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
};

export default function GeneratePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const setProject = useProjectStore((s) => s.setProject);
  const setScenes = useProjectStore((s) => s.setScenes);
  const updateScene = useProjectStore((s) => s.updateScene);
  const scenes = useProjectStore((s) => s.scenes);
  const setPreviewUrl = useProjectStore((s) => s.setPreviewUrl);
  const setJobStatus = useProjectStore((s) => s.setJobStatus);
  const setSelectedSceneId = useProjectStore((s) => s.setSelectedSceneId);
  const selectedSceneId = useProjectStore((s) => s.selectedSceneId);

  const [loading, setLoading] = useState(false);
  const [projectLoaded, setProjectLoaded] = useState(false);
  const autoStarted = useRef(false);
  const autoPromptRef = useRef(searchParams.get("prompt"));

  const selectedScene = scenes.find((s) => s.id === selectedSceneId) ?? null;

  // Chat state
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatRefining, setChatRefining] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const prevStatusRef = useRef<string | null>(null);
  const seenSceneRef = useRef<string | null>(null);

  // autoStartPending: true when we arrived with a ?prompt — shows spinner
  // immediately instead of the "Generate a scene" empty state
  const [autoStartPending, setAutoStartPending] = useState(
    () => searchParams.has("prompt")
  );
  const [showComingSoon, setShowComingSoon] = useState(false);

  // ── Clean ?prompt= from URL on mount so page refresh never re-triggers the spinner ──
  useEffect(() => {
    if (searchParams.has("prompt")) {
      window.history.replaceState(null, "", `/project/${params.id}/generate`);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Project load ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!params.id) return;
    // Clear stale state from any previous project immediately so the old video
    // never bleeds into the new project while the fetch is in flight.
    setScenes([]);
    setPreviewUrl(null);
    setSelectedSceneId(null);
    void Promise.all([
      getProject(params.id),
      getChatMessages(params.id).catch(() => []),
    ]).then(([detail, savedMessages]) => {
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
            videoUrl: s.video_preview_path ?? null,
            thumbnailUrl: s.thumbnail_path ? assetUrl(s.thumbnail_path) : null,
            prompt: latest?.prompt ?? "",
            manimCode: latest?.manim_code ?? "",
            status: latest?.validation_status === "valid" ? "complete" : "idle",
            progress: 0,
          };
        });
      setScenes(timeline);
      // Restore persisted chat history
      if (savedMessages.length > 0) {
        setChat(savedMessages.map((m) => ({ id: m.id, role: m.role as "user" | "assistant", content: m.content })));
        seenSceneRef.current = timeline.find((s) => s.videoUrl)?.id ?? null;
      }
      // Auto-select the first scene that has a video so it shows immediately on refresh
      const firstWithVideo = timeline.find((s) => s.videoUrl) ?? timeline[0];
      if (firstWithVideo) setSelectedSceneId(firstWithVideo.id);
      setProjectLoaded(true);
    }).catch(() => { setProjectLoaded(true); });
  }, [params.id, setProject, setScenes, setSelectedSceneId]);

  // ── Auto-start from landing page prompt ───────────────────────────────────
  useEffect(() => {
    if (!projectLoaded) return;
    const autoPrompt = autoPromptRef.current;
    if (!autoPrompt || autoStarted.current) return;
    // Project already has scenes (e.g. page refresh) — clear the spinner and show the video
    if (scenes.length > 0) {
      setAutoStartPending(false);
      return;
    }
    autoStarted.current = true;
    setAutoStartPending(false);
    void handleGenerate(decodeURIComponent(autoPrompt), "technical-clean", 30, "16:9");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectLoaded, scenes.length]);

  // ── Chat: auto-scroll to bottom ───────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  // ── Chat: welcome message when scene first becomes ready (video loaded) ───
  useEffect(() => {
    if (!selectedScene) return;
    if (seenSceneRef.current === selectedScene.id) return;
    if (selectedScene.status !== "complete" || !selectedScene.videoUrl) return;
    seenSceneRef.current = selectedScene.id;
    const welcome = "Your animation is ready! Tell me what you'd like to change and I'll refine the code and re-render it for you.";
    setChat([{ id: "welcome", role: "assistant", content: welcome }]);
    void addChatMessage(params.id!, "assistant", welcome).catch(() => {});
  }, [selectedScene?.id, selectedScene?.status, selectedScene?.videoUrl, params.id]);

  // ── Chat: respond when refine job completes or fails ─────────────────────
  useEffect(() => {
    if (!chatRefining || !selectedScene) return;
    const { status } = selectedScene;
    if (status === prevStatusRef.current) return;
    prevStatusRef.current = status;
    if (status === "complete") {
      const msg = "Done! The animation has been updated — check the video on the left.";
      setChat((prev) => [...prev.filter((m) => !m.pending), { id: `a-${Date.now()}`, role: "assistant", content: msg }]);
      void addChatMessage(params.id!, "assistant", msg).catch(() => {});
      setChatRefining(false);
    } else if (status === "error") {
      const msg = "Something went wrong with that change. Try rephrasing your request or use Regenerate from Scratch.";
      setChat((prev) => [...prev.filter((m) => !m.pending), { id: `a-${Date.now()}`, role: "assistant", content: msg }]);
      void addChatMessage(params.id!, "assistant", msg).catch(() => {});
      setChatRefining(false);
    }
  }, [selectedScene?.status, chatRefining]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  async function handleGenerate(prompt: string, style: string, duration: number, aspect: string) {
    if (!params.id) return;
    setLoading(true);
    try {
      const res = await generateScene({
        project_id: params.id,
        prompt,
        style_preset: style,
        max_duration_sec: duration,
        aspect_ratio: aspect,
      });
      const newScene: TimelineScene = {
        id: res.scene_id,
        sceneNumber: scenes.length + 1,
        description: prompt,
        duration,
        videoUrl: null,
        thumbnailUrl: null,
        prompt,
        manimCode: "",
        status: "generating_code",
        progress: 0,
      };
      setScenes([...scenes, newScene]);
      setSelectedSceneId(res.scene_id);
      setJobStatus(res.preview_job_id, "running", 0);
      pollJob(res.preview_job_id, res.scene_id);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }

  function pollJob(jobId: string, sceneId: string) {
    let errorCount = 0;
    const interval = setInterval(async () => {
      try {
        const job = await getJob(jobId);
        errorCount = 0;
        if (job.status === "running" || job.status === "queued") {
          const progress = job.status === "queued" ? 10 : 50;
          updateScene(sceneId, { status: job.status === "queued" ? "generating_code" : "rendering_video", progress });
          setJobStatus(jobId, job.status, progress);
        } else if (job.status === "completed") {
          clearInterval(interval);
          const videoAsset = job.assets.find((a) => a.asset_type === "video_preview");
          updateScene(sceneId, {
            status: "complete",
            progress: 100,
            videoUrl: videoAsset?.storage_path ?? null,
          });
          setJobStatus(jobId, "completed", 100);
          if (videoAsset) setPreviewUrl(videoAsset.storage_path);
          setSelectedSceneId(sceneId);
        } else if (job.status === "failed") {
          clearInterval(interval);
          updateScene(sceneId, { status: "error", progress: 0 });
          setJobStatus(jobId, "failed", 0);
        }
      } catch {
        errorCount++;
        if (errorCount >= 5) {
          clearInterval(interval);
          updateScene(sceneId, { status: "error", progress: 0 });
          setJobStatus(jobId, "failed", 0);
        }
      }
    }, 2000);
  }

  async function handleRegenerate(sceneId: string, overridePrompt?: string) {
    const scene = scenes.find((s) => s.id === sceneId);
    if (!scene) return;
    const prompt = overridePrompt ?? scene.prompt;
    updateScene(sceneId, { status: "generating_code", progress: 0, prompt });
    setSelectedSceneId(sceneId);
    try {
      const res = await regenerateScene(sceneId, {
        prompt,
        style_preset: "technical-clean",
        max_duration_sec: scene.duration,
        aspect_ratio: "16:9",
      });
      pollJob(res.preview_job_id, sceneId);
    } catch {
      updateScene(sceneId, { status: "error", progress: 0 });
    }
  }

  async function handleRenderHD(sceneId: string) {
    try {
      const res = await renderHD(sceneId);
      setJobStatus(res.job_id, "running", 0);
      updateScene(sceneId, { status: "rendering_video", progress: 20 });
      setSelectedSceneId(sceneId);
      pollJob(res.job_id, sceneId);
    } catch { /* silent */ }
  }

  async function handleRefine(sceneId: string, feedback: string) {
    updateScene(sceneId, { status: "generating_code", progress: 0 });
    setSelectedSceneId(sceneId);
    try {
      const res = await refineScene(sceneId, feedback);
      setJobStatus(res.preview_job_id, "running", 0);
      pollJob(res.preview_job_id, sceneId);
    } catch {
      updateScene(sceneId, { status: "error", progress: 0 });
    }
  }

  function handleChatSend() {
    const msg = chatInput.trim();
    if (!msg || !selectedScene || chatRefining) return;
    if (selectedScene.status === "generating_code" || selectedScene.status === "rendering_video") return;

    prevStatusRef.current = selectedScene.status;
    setChat((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content: msg },
      { id: "pending", role: "assistant", content: "", pending: true },
    ]);
    void addChatMessage(params.id!, "user", msg).catch(() => {});
    setChatInput("");
    setChatRefining(true);
    void handleRefine(selectedScene.id, msg);
  }

  const isBusy = selectedScene?.status === "generating_code" || selectedScene?.status === "rendering_video";

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      <Sidebar />
      <main
        className="animate-fade-in"
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          background: "var(--bg)",
        }}
      >
        {/* Prompt bar — DISABLED: hidden from users, code retained for future re-enable */}
        <div style={{ display: "none" }}>
          <PromptInput onGenerate={handleGenerate} loading={loading} />
        </div>

        {/* Content */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

          {/* Center: full video player */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              padding: "16px",
            }}
          >
            <VideoPreview forceLoading={!projectLoaded || autoStartPending} />
          </div>

          {/* Right: AI chat panel */}
          <div
            style={{
              width: "340px",
              flexShrink: 0,
              borderLeft: "1px solid var(--border)",
              background: "var(--surface)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {/* Scene status header */}
            <div
              style={{
                padding: "12px 14px",
                borderBottom: "1px solid var(--border)",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                flexShrink: 0,
              }}
            >
              {selectedScene ? (
                <>
                  <span
                    className={`badge ${
                      selectedScene.status === "complete" ? "badge-complete"
                      : selectedScene.status === "error" ? "badge-error"
                      : selectedScene.status === "rendering_video" ? "badge-rendering"
                      : selectedScene.status === "generating_code" ? "badge-generating"
                      : "badge-idle"
                    }`}
                  >
                    {selectedScene.status === "generating_code" ? "Writing Code"
                      : selectedScene.status === "rendering_video" ? "Rendering"
                      : selectedScene.status === "complete" ? "Complete"
                      : selectedScene.status === "error" ? "Error"
                      : "Idle"}
                  </span>
                  <span
                    style={{
                      fontSize: "11px",
                      color: "var(--text-3)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      flex: 1,
                    }}
                  >
                    {selectedScene.description}
                  </span>
                  <span style={{ fontSize: "10px", color: "var(--text-3)", fontFamily: "var(--font-mono)", flexShrink: 0 }}>
                    {selectedScene.duration}s
                  </span>
                </>
              ) : (
                <span style={{ fontSize: "12px", color: "var(--text-3)" }}>No animation yet</span>
              )}
            </div>

            {/* Chat messages */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "14px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              {chat.length === 0 && (
                <div
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "10px",
                    color: "var(--text-3)",
                    textAlign: "center",
                    padding: "20px",
                  }}
                >
                  <div
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "50%",
                      border: "1px solid var(--border-mid)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "18px",
                    }}
                  >
                    ✦
                  </div>
                  <p style={{ fontSize: "12px", margin: 0, lineHeight: 1.6 }}>
                    Generate an animation,<br />then chat here to refine it.
                  </p>
                </div>
              )}

              {chat.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    display: "flex",
                    justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                  }}
                >
                  <div
                    style={{
                      maxWidth: "82%",
                      padding: msg.pending ? "10px 14px" : "9px 13px",
                      borderRadius: msg.role === "user"
                        ? "14px 14px 3px 14px"
                        : "14px 14px 14px 3px",
                      background: msg.role === "user"
                        ? "var(--amber)"
                        : "var(--card)",
                      color: msg.role === "user" ? "#09090A" : "var(--text-2)",
                      fontSize: "13px",
                      lineHeight: 1.55,
                      border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
                    }}
                  >
                    {msg.pending ? (
                      /* Animated thinking dots */
                      <div style={{ display: "flex", gap: "5px", alignItems: "center", height: "14px" }}>
                        {[0, 1, 2].map((i) => (
                          <div
                            key={i}
                            style={{
                              width: "6px",
                              height: "6px",
                              borderRadius: "50%",
                              background: "var(--text-3)",
                              animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                            }}
                          />
                        ))}
                      </div>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Chat input */}
            <div
              style={{
                padding: "10px 12px",
                borderTop: "1px solid var(--border)",
                display: "flex",
                gap: "8px",
                alignItems: "flex-end",
                flexShrink: 0,
              }}
            >
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleChatSend();
                  }
                }}
                placeholder={
                  !selectedScene
                    ? "Generate an animation first…"
                    : isBusy
                    ? "Rendering, please wait…"
                    : "Ask for a change… (Enter to send)"
                }
                disabled={!selectedScene || isBusy || chatRefining}
                rows={2}
                style={{
                  flex: 1,
                  background: "var(--bg)",
                  border: "1px solid var(--border-mid)",
                  borderRadius: "10px",
                  padding: "8px 11px",
                  color: "var(--text)",
                  fontSize: "13px",
                  fontFamily: "var(--font-dm-sans)",
                  lineHeight: 1.5,
                  resize: "none",
                  outline: "none",
                  transition: "border-color 0.15s",
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = "var(--amber)"; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border-mid)"; }}
              />
              <button
                onClick={handleChatSend}
                disabled={!chatInput.trim() || !selectedScene || isBusy || chatRefining}
                style={{
                  width: "36px",
                  height: "36px",
                  flexShrink: 0,
                  borderRadius: "10px",
                  border: "none",
                  background: chatInput.trim() && selectedScene && !isBusy && !chatRefining
                    ? "var(--amber)"
                    : "var(--card)",
                  color: chatInput.trim() && selectedScene && !isBusy && !chatRefining
                    ? "#09090A"
                    : "var(--text-3)",
                  cursor: chatInput.trim() && selectedScene && !isBusy && !chatRefining
                    ? "pointer"
                    : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "16px",
                  transition: "all 0.15s",
                }}
              >
                ↑
              </button>
            </div>

            {/* Footer actions */}
            <div
              style={{
                padding: "10px 12px",
                borderTop: "1px solid var(--border)",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                flexShrink: 0,
              }}
            >
              {/* Regenerate from Scratch — DISABLED: hidden, code retained */}
              <div style={{ display: "none" }}>
                <button
                  className="btn-outline"
                  style={{ width: "100%", fontSize: "11px" }}
                  disabled={!selectedScene || isBusy || chatRefining}
                  onClick={() => {
                    if (selectedScene) void handleRegenerate(selectedScene.id);
                  }}
                >
                  Regenerate from Scratch
                </button>
              </div>
              {params.id && (
                <button
                  onClick={() => setShowComingSoon(true)}
                  className="btn-outline"
                  style={{ width: "100%", fontSize: "11px" }}
                >
                  Open in Editor →
                </button>
              )}
            </div>
          </div>
        </div>
      </main>
      {/* Coming Soon modal */}
      {showComingSoon && (
        <div
          onClick={() => setShowComingSoon(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(9,9,10,0.88)",
            backdropFilter: "blur(14px)",
            WebkitBackdropFilter: "blur(14px)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: "fadeIn 0.2s ease forwards",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--card)",
              border: "1px solid var(--border-mid)",
              borderRadius: "24px",
              padding: "48px 44px 40px",
              maxWidth: "400px",
              width: "90%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "24px",
              textAlign: "center",
              animation: "fadeUp 0.3s ease forwards",
              position: "relative",
              boxShadow: "0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px var(--border)",
            }}
          >
            {/* Animated graphic */}
            <div style={{ position: "relative", width: "96px", height: "96px" }}>
              {/* Ambient glow */}
              <div style={{
                position: "absolute",
                inset: "-16px",
                borderRadius: "50%",
                background: "radial-gradient(circle, rgba(245,158,11,0.14) 0%, transparent 70%)",
                pointerEvents: "none",
              }} />
              {/* Outer orbit ring */}
              <div style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                border: "1px solid var(--border)",
              }} />
              {/* Outer orbiting dot */}
              <div style={{
                position: "absolute",
                inset: 0,
                borderRadius: "50%",
                animation: "spin 3.5s linear infinite",
              }}>
                <div style={{
                  position: "absolute",
                  top: "-5px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: "10px",
                  height: "10px",
                  borderRadius: "50%",
                  background: "var(--amber)",
                  boxShadow: "0 0 10px rgba(245,158,11,0.8), 0 0 20px rgba(245,158,11,0.4)",
                }} />
              </div>
              {/* Inner orbit ring */}
              <div style={{
                position: "absolute",
                inset: "18px",
                borderRadius: "50%",
                border: "1px solid var(--border-mid)",
              }} />
              {/* Inner orbiting dot */}
              <div style={{
                position: "absolute",
                inset: "18px",
                borderRadius: "50%",
                animation: "spinReverse 2.2s linear infinite",
              }}>
                <div style={{
                  position: "absolute",
                  top: "-4px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  background: "rgba(245,158,11,0.55)",
                }} />
              </div>
              {/* Center */}
              <div style={{
                position: "absolute",
                inset: "34px",
                borderRadius: "50%",
                background: "var(--card-hover)",
                border: "1px solid var(--border-mid)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "13px",
                color: "var(--amber)",
                fontFamily: "var(--font-mono)",
                boxShadow: "0 0 12px rgba(245,158,11,0.15)",
              }}>
                ✦
              </div>
            </div>

            {/* Text */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <h2 style={{
                margin: 0,
                fontFamily: "var(--font-syne)",
                fontSize: "26px",
                fontWeight: 800,
                letterSpacing: "-0.03em",
                color: "var(--text)",
              }}>
                Coming Soon
              </h2>
              <p style={{
                margin: 0,
                fontSize: "14px",
                color: "var(--text-2)",
                lineHeight: 1.65,
                maxWidth: "280px",
              }}>
                The code editor is being crafted.<br />
                Full control over your animations — coming soon.
              </p>
            </div>

            {/* Close button */}
            <button
              onClick={() => setShowComingSoon(false)}
              className="btn-amber"
              style={{ padding: "10px 32px", fontSize: "13px" }}
            >
              Got it
            </button>

            {/* Dismiss hint */}
            <p style={{ margin: 0, fontSize: "11px", color: "var(--text-3)" }}>
              Click anywhere outside to close
            </p>
          </div>
        </div>
      )}
    </>
  );
}
