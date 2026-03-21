"use client";

import { useState, useEffect } from "react";
import { listPresets } from "@/lib/api";
import type { StylePreset } from "@/lib/types";

interface Props {
  onGenerate: (prompt: string, style: string, duration: number, aspect: string) => void;
  loading?: boolean;
}

export default function PromptInput({ onGenerate, loading }: Props) {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("technical-clean");
  const [duration, setDuration] = useState(30);
  const [aspect, setAspect] = useState("16:9");
  const [presets, setPresets] = useState<StylePreset[]>([]);

  useEffect(() => {
    void listPresets().then(setPresets).catch(() => {});
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    onGenerate(prompt.trim(), style, duration, aspect);
    setPrompt("");
  }

  return (
    <form onSubmit={handleSubmit}>
      <div
        style={{
          display: "flex",
          gap: "10px",
          alignItems: "flex-end",
        }}
      >
        {/* Prompt textarea */}
        <div style={{ flex: 1, position: "relative" }}>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe your animation scene…"
            rows={2}
            className="field"
            style={{
              resize: "none",
              paddingRight: "12px",
              lineHeight: 1.5,
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
        </div>

        {/* Controls column */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", flexShrink: 0 }}>
          <div style={{ display: "flex", gap: "6px" }}>
            {/* Style */}
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="field"
              style={{ fontSize: "11px", padding: "7px 8px", width: "140px" }}
            >
              {presets.length === 0 ? (
                <option value={style}>{style}</option>
              ) : (
                presets.map((p) => (
                  <option key={p.id} value={p.id}>{p.display_name}</option>
                ))
              )}
            </select>

            {/* Duration */}
            <input
              type="number"
              min={1}
              max={60}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="field"
              style={{ fontSize: "11px", padding: "7px 8px", width: "58px", textAlign: "center" }}
              title="Duration (sec)"
            />

            {/* Aspect */}
            <input
              value={aspect}
              onChange={(e) => setAspect(e.target.value)}
              className="field"
              style={{ fontSize: "11px", padding: "7px 8px", width: "58px", textAlign: "center" }}
              title="Aspect ratio"
            />
          </div>
        </div>

        {/* Generate button */}
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="btn-amber"
          style={{ flexShrink: 0, padding: "10px 20px", fontSize: "12px" }}
        >
          {loading ? (
            <>
              <span
                style={{
                  width: "11px",
                  height: "11px",
                  border: "2px solid rgba(9,9,10,0.3)",
                  borderTopColor: "#09090A",
                  borderRadius: "50%",
                  animation: "spin 0.7s linear infinite",
                  display: "inline-block",
                }}
              />
              Generating…
            </>
          ) : (
            "Generate →"
          )}
        </button>
      </div>
    </form>
  );
}
