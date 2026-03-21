"use client";

import { useState } from "react";
import type { TimelineScene } from "@/lib/types";
import { formatDuration } from "@/lib/utils";

interface Props {
  scene: TimelineScene;
  index: number;
  selected?: boolean;
  onSelect: () => void;
  onMoveLeft: () => void;
  onMoveRight: () => void;
  isFirst: boolean;
  isLast: boolean;
}

const STATUS_COLOR: Record<string, string> = {
  idle:            "#3D4047",
  generating_code: "#EAB308",
  rendering_video: "#60A5FA",
  complete:        "#4ADE80",
  error:           "#F87171",
};

export default function TimelineTrack({
  scene,
  selected,
  onSelect,
  onMoveLeft,
  onMoveRight,
  isFirst,
  isLast,
}: Props) {
  const [hovered, setHovered] = useState(false);
  const color = STATUS_COLOR[scene.status] ?? "#3D4047";

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flexShrink: 0,
        width: "130px",
        borderRadius: "9px",
        border: `1px solid ${selected ? "var(--amber)" : hovered ? "var(--border-mid)" : "var(--border)"}`,
        background: selected ? "var(--amber-10)" : hovered ? "var(--card-hover)" : "var(--card)",
        cursor: "pointer",
        transition: "border-color 0.12s, background 0.12s",
        overflow: "hidden",
      }}
    >
      {/* Status bar */}
      <div
        style={{
          height: "2px",
          background: color,
          opacity: 0.7,
        }}
      />

      {/* Thumbnail */}
      <div
        style={{
          aspectRatio: "16/9",
          background: "#0A0A0B",
          overflow: "hidden",
          position: "relative",
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
              alignItems: "center",
              justifyContent: "center",
              color: color,
              fontSize: "11px",
              fontFamily: "var(--font-mono)",
            }}
          >
            {scene.status === "complete" ? "✓" : scene.status === "error" ? "✗" : "…"}
          </div>
        )}
      </div>

      {/* Info + controls */}
      <div style={{ padding: "6px 7px 7px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "5px",
          }}
        >
          <span
            style={{
              fontSize: "10px",
              fontWeight: 700,
              color: selected ? "var(--amber)" : "var(--text-2)",
              fontFamily: "var(--font-syne)",
            }}
          >
            S{String(scene.sceneNumber).padStart(2, "0")}
          </span>
          <span
            style={{
              fontSize: "9px",
              color: "var(--text-3)",
              fontFamily: "var(--font-mono)",
            }}
          >
            {formatDuration(scene.duration)}
          </span>
        </div>

        {/* Reorder buttons */}
        <div style={{ display: "flex", gap: "4px" }}>
          <button
            onClick={(e) => { e.stopPropagation(); onMoveLeft(); }}
            disabled={isFirst}
            style={{
              flex: 1,
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: "5px",
              padding: "3px 0",
              fontSize: "10px",
              color: isFirst ? "var(--text-3)" : "var(--text-2)",
              cursor: isFirst ? "not-allowed" : "pointer",
              opacity: isFirst ? 0.35 : 1,
              transition: "border-color 0.12s, color 0.12s",
            }}
            onMouseEnter={(e) => {
              if (!isFirst) {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border-mid)";
                (e.currentTarget as HTMLElement).style.color = "var(--text)";
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
              (e.currentTarget as HTMLElement).style.color = isFirst ? "var(--text-3)" : "var(--text-2)";
            }}
          >
            ←
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onMoveRight(); }}
            disabled={isLast}
            style={{
              flex: 1,
              background: "transparent",
              border: "1px solid var(--border)",
              borderRadius: "5px",
              padding: "3px 0",
              fontSize: "10px",
              color: isLast ? "var(--text-3)" : "var(--text-2)",
              cursor: isLast ? "not-allowed" : "pointer",
              opacity: isLast ? 0.35 : 1,
              transition: "border-color 0.12s, color 0.12s",
            }}
            onMouseEnter={(e) => {
              if (!isLast) {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border-mid)";
                (e.currentTarget as HTMLElement).style.color = "var(--text)";
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
              (e.currentTarget as HTMLElement).style.color = isLast ? "var(--text-3)" : "var(--text-2)";
            }}
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
