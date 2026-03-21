"use client";

import { useProjectStore } from "@/store/useProjectStore";
import SceneCard from "./SceneCard";

interface Props {
  onRegenerate?: (sceneId: string, prompt?: string) => void;
  onRenderHD?: (sceneId: string) => void;
  onRefine?: (sceneId: string, feedback: string) => void;
}

export default function SceneList({ onRegenerate, onRenderHD, onRefine }: Props) {
  const scenes = useProjectStore((s) => s.scenes);
  const selectedSceneId = useProjectStore((s) => s.selectedSceneId);
  const setSelectedSceneId = useProjectStore((s) => s.setSelectedSceneId);
  const removeScene = useProjectStore((s) => s.removeScene);

  if (scenes.length === 0) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "12px",
          padding: "40px",
          color: "var(--text-3)",
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "16px",
            border: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "24px",
          }}
        >
          ◇
        </div>
        <p style={{ fontSize: "13px", textAlign: "center", lineHeight: 1.5, margin: 0 }}>
          No scenes yet.
          <br />
          Describe your animation above and hit Generate.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: "12px",
        padding: "16px",
      }}
    >
      {scenes.map((scene) => (
        <SceneCard
          key={scene.id}
          scene={scene}
          selected={selectedSceneId === scene.id}
          onSelect={() => setSelectedSceneId(scene.id)}
          onRegenerate={onRegenerate ? (prompt?: string) => onRegenerate(scene.id, prompt) : undefined}
          onRenderHD={onRenderHD ? () => onRenderHD(scene.id) : undefined}
          onRefine={onRefine ? (feedback: string) => onRefine(scene.id, feedback) : undefined}
          onRemove={() => removeScene(scene.id)}
        />
      ))}
    </div>
  );
}
