"use client";

import { useProjectStore } from "@/store/useProjectStore";
import TimelineTrack from "./TimelineTrack";

export default function SceneTimeline() {
  const scenes = useProjectStore((s) => s.scenes);
  const selectedSceneId = useProjectStore((s) => s.selectedSceneId);
  const setSelectedSceneId = useProjectStore((s) => s.setSelectedSceneId);
  const reorderScenes = useProjectStore((s) => s.reorderScenes);

  function handleMoveLeft(idx: number) {
    if (idx <= 0) return;
    reorderScenes(idx, idx - 1);
  }

  function handleMoveRight(idx: number) {
    if (idx >= scenes.length - 1) return;
    reorderScenes(idx, idx + 1);
  }

  const totalDuration = scenes.reduce((sum, s) => sum + s.duration, 0);

  if (scenes.length === 0) {
    return (
      <div
        style={{
          height: "80px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderTop: "1px solid var(--border)",
          background: "var(--bg)",
          color: "var(--text-3)",
          fontSize: "11px",
          letterSpacing: "0.06em",
        }}
      >
        Timeline is empty — generate scenes to populate
      </div>
    );
  }

  return (
    <div
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg)",
        flexShrink: 0,
      }}
    >
      {/* Timeline header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "6px 14px 0",
        }}
      >
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--text-3)",
          }}
        >
          Timeline · {scenes.length} scene{scenes.length !== 1 ? "s" : ""}
        </span>
        <span
          style={{
            fontSize: "10px",
            color: "var(--text-3)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {totalDuration}s total
        </span>
      </div>

      {/* Tracks */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          overflowX: "auto",
          padding: "8px 14px 10px",
        }}
      >
        {scenes.map((scene, idx) => (
          <TimelineTrack
            key={scene.id}
            scene={scene}
            index={idx}
            selected={selectedSceneId === scene.id}
            onSelect={() => setSelectedSceneId(scene.id)}
            onMoveLeft={() => handleMoveLeft(idx)}
            onMoveRight={() => handleMoveRight(idx)}
            isFirst={idx === 0}
            isLast={idx === scenes.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
