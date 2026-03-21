"use client";

import { useProjectStore } from "@/store/useProjectStore";

export default function CodeEditor() {
  const scenes = useProjectStore((s) => s.scenes);
  const selectedSceneId = useProjectStore((s) => s.selectedSceneId);
  const updateScene = useProjectStore((s) => s.updateScene);

  const scene = scenes.find((s) => s.id === selectedSceneId);

  if (!scene) {
    return (
      <div
        style={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "10px",
          color: "var(--text-3)",
        }}
      >
        <span style={{ fontSize: "20px" }}>{ }</span>
        <p style={{ fontSize: "12px", margin: 0, textAlign: "center", lineHeight: 1.5 }}>
          Select a scene to<br />view its Manim code
        </p>
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "9px 14px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
          background: "var(--surface)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              display: "flex",
              gap: "4px",
            }}
          >
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--border-mid)" }} />
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--border-mid)" }} />
            <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--border-mid)" }} />
          </div>
          <span
            style={{
              fontSize: "11px",
              color: "var(--text-3)",
              fontFamily: "var(--font-mono)",
            }}
          >
            scene_{String(scene.sceneNumber).padStart(2, "0")}.py
          </span>
        </div>
        <span
          style={{
            fontSize: "10px",
            color: scene.status === "complete" ? "#4ADE80" : "var(--text-3)",
            fontWeight: 600,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          {scene.status}
        </span>
      </div>

      {/* Code area */}
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {/* Line numbers background hint */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: "40px",
            background: "rgba(0,0,0,0.2)",
            borderRight: "1px solid var(--border)",
            pointerEvents: "none",
          }}
        />
        <textarea
          value={scene.manimCode}
          onChange={(e) => updateScene(scene.id, { manimCode: e.target.value })}
          spellCheck={false}
          style={{
            width: "100%",
            height: "100%",
            background: "var(--bg)",
            color: "#B5C0D0",
            fontSize: "12.5px",
            fontFamily: "var(--font-mono)",
            lineHeight: "1.65",
            padding: "14px 14px 14px 52px",
            border: "none",
            outline: "none",
            resize: "none",
            tabSize: 4,
          }}
        />
      </div>
    </div>
  );
}
