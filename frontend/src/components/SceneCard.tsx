"use client";

import { useState } from "react";
import type { TimelineScene } from "@/lib/types";
import { cn, formatDuration } from "@/lib/utils";

interface Props {
  scene: TimelineScene;
  selected?: boolean;
  onSelect?: () => void;
  onRegenerate?: (prompt?: string) => void;
  onRenderHD?: () => void;
  onRefine?: (feedback: string) => void;
  onRemove?: () => void;
}

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  idle:            { label: "Idle",       cls: "badge-idle" },
  generating_code: { label: "Generating", cls: "badge-generating" },
  rendering_video: { label: "Rendering",  cls: "badge-rendering" },
  complete:        { label: "Complete",   cls: "badge-complete" },
  error:           { label: "Error",      cls: "badge-error" },
};

export default function SceneCard({ scene, selected, onSelect, onRegenerate, onRenderHD, onRefine, onRemove }: Props) {
  const [hovered, setHovered] = useState(false);
  const [showRefine, setShowRefine] = useState(false);
  const [refineFeedback, setRefineFeedback] = useState("");

  const cfg = STATUS_CONFIG[scene.status] ?? STATUS_CONFIG.idle;
  const isProcessing = scene.status === "generating_code" || scene.status === "rendering_video";

  function handleApplyRefine(e: React.MouseEvent) {
    e.stopPropagation();
    if (!refineFeedback.trim()) return;
    onRefine?.(refineFeedback.trim());
    setShowRefine(false);
    setRefineFeedback("");
  }

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: "var(--card)",
        border: `1px solid ${selected ? "var(--amber)" : hovered ? "var(--border-mid)" : "var(--border)"}`,
        borderRadius: "12px",
        cursor: "pointer",
        transition: "border-color 0.15s, transform 0.15s, box-shadow 0.15s",
        transform: hovered && !selected ? "translateY(-2px)" : "none",
        boxShadow: selected
          ? "0 0 0 1px var(--amber-10), 0 0 20px rgba(245,158,11,0.08)"
          : hovered
          ? "0 8px 24px rgba(0,0,0,0.4)"
          : "none",
        overflow: "hidden",
      }}
    >
      {/* Thumbnail */}
      <div
        style={{
          position: "relative",
          aspectRatio: "16/9",
          background: "#0C0C0D",
          overflow: "hidden",
        }}
      >
        {scene.thumbnailUrl ? (
          <img
            src={scene.thumbnailUrl}
            alt={`Scene ${scene.sceneNumber}`}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : (
          <div
            style={{
              width: "100%",
              height: "100%",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
            }}
          >
            {isProcessing ? (
              <>
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    border: "2px solid var(--border-mid)",
                    borderTopColor: "var(--amber)",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite",
                  }}
                />
                <span style={{ fontSize: "10px", color: "var(--text-3)" }}>
                  {scene.status === "generating_code" ? "Writing Manim code…" : "Rendering preview…"}
                </span>
              </>
            ) : (
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "50%",
                  border: "1px solid var(--border-mid)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--text-3)",
                  fontSize: "16px",
                }}
              >
                {scene.status === "error" ? "!" : "◇"}
              </div>
            )}
          </div>
        )}

        {/* Scene number */}
        <div
          style={{
            position: "absolute",
            top: "8px",
            left: "8px",
            background: "rgba(9,9,10,0.8)",
            backdropFilter: "blur(4px)",
            border: "1px solid var(--border-mid)",
            borderRadius: "6px",
            padding: "2px 7px",
            fontSize: "10px",
            fontWeight: 600,
            color: "var(--text-2)",
            fontFamily: "var(--font-syne)",
          }}
        >
          {String(scene.sceneNumber).padStart(2, "0")}
        </div>

        {/* Status badge */}
        <div style={{ position: "absolute", top: "8px", right: "8px" }}>
          <span className={cn("badge", cfg.cls)}>{cfg.label}</span>
        </div>

        {/* Hover action overlay — shown on complete scenes */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(9,9,10,0.85)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            opacity: hovered && scene.status === "complete" ? 1 : 0,
            transition: "opacity 0.15s",
            pointerEvents: hovered && scene.status === "complete" ? "auto" : "none",
          }}
        >
          {onRegenerate && (
            <button
              className="btn-outline"
              style={{ fontSize: "11px", padding: "6px 12px" }}
              onClick={(e) => { e.stopPropagation(); onRegenerate(); }}
            >
              ↻ Regen
            </button>
          )}
          {onRefine && (
            <button
              className="btn-amber"
              style={{ fontSize: "11px", padding: "6px 12px" }}
              onClick={(e) => { e.stopPropagation(); setShowRefine((v) => !v); }}
            >
              ✎ Refine
            </button>
          )}
          {onRenderHD && (
            <button
              className="btn-outline"
              style={{ fontSize: "11px", padding: "6px 12px" }}
              onClick={(e) => { e.stopPropagation(); onRenderHD(); }}
            >
              ⬆ HD
            </button>
          )}
        </div>
      </div>

      {/* Card body */}
      <div style={{ padding: "10px 12px 12px" }}>
        <p
          style={{
            fontSize: "12px",
            color: "var(--text-2)",
            lineHeight: 1.45,
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            margin: 0,
            marginBottom: "8px",
          }}
        >
          {scene.description}
        </p>

        {/* Inline refine input */}
        {showRefine && (
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ marginBottom: "8px", display: "flex", flexDirection: "column", gap: "6px" }}
          >
            <textarea
              value={refineFeedback}
              onChange={(e) => setRefineFeedback(e.target.value)}
              placeholder="Describe what needs to be fixed…"
              rows={2}
              autoFocus
              className="field"
              style={{ fontSize: "11px", padding: "7px 9px", resize: "none", lineHeight: 1.4 }}
            />
            <div style={{ display: "flex", gap: "5px" }}>
              <button
                className="btn-amber"
                style={{ flex: 1, fontSize: "11px", padding: "6px" }}
                onClick={handleApplyRefine}
                disabled={!refineFeedback.trim()}
              >
                Apply
              </button>
              <button
                className="btn-ghost"
                style={{ fontSize: "11px", padding: "6px 10px" }}
                onClick={(e) => { e.stopPropagation(); setShowRefine(false); setRefineFeedback(""); }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "11px", color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>
            {formatDuration(scene.duration)}
          </span>

          <div style={{ display: "flex", gap: "4px", alignItems: "center" }}>
            {isProcessing && scene.progress > 0 && scene.progress < 100 && (
              <span style={{ fontSize: "10px", color: "var(--amber)" }}>{Math.round(scene.progress)}%</span>
            )}
            {onRemove && (
              <button
                className="btn-ghost"
                style={{ color: "var(--text-3)", padding: "3px 6px", fontSize: "11px" }}
                onClick={(e) => { e.stopPropagation(); onRemove(); }}
                title="Remove scene"
              >
                ✕
              </button>
            )}
            {onRegenerate && scene.status !== "complete" && (
              <button
                className="btn-ghost"
                style={{ padding: "3px 6px", fontSize: "11px" }}
                onClick={(e) => { e.stopPropagation(); onRegenerate(); }}
                title="Regenerate"
              >
                ↻
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        {isProcessing && (
          <>
            <div style={{ fontSize: "10px", color: "var(--text-3)", marginTop: "6px", marginBottom: "4px" }}>
              {scene.status === "generating_code" ? "Writing Manim code…" : "Rendering preview…"}
            </div>
            <div className="progress-track">
              {scene.progress > 0 && scene.progress < 100 ? (
                <div className="progress-fill" style={{ width: `${scene.progress}%` }} />
              ) : (
                <div className="progress-fill progress-fill-indeterminate" />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
