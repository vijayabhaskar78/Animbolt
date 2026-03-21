"use client";

import { useState } from "react";
import { useProjectStore } from "@/store/useProjectStore";
import { generateTTS, uploadVoiceover } from "@/lib/api";

export default function VoiceoverPanel() {
  const projectId = useProjectStore((s) => s.projectId);
  const script = useProjectStore((s) => s.voiceoverScript);
  const setScript = useProjectStore((s) => s.setVoiceoverScript);
  const voice = useProjectStore((s) => s.voiceoverVoice);
  const setVoice = useProjectStore((s) => s.setVoiceoverVoice);
  const setVoiceoverUrl = useProjectStore((s) => s.setVoiceoverUrl);

  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ text: string; ok: boolean } | null>(null);

  async function handleGenerate() {
    if (!projectId || !script.trim()) return;
    setBusy(true);
    setStatus(null);
    try {
      const res = await generateTTS({ project_id: projectId, text: script, voice });
      setVoiceoverUrl(res.storage_path);
      setStatus({ text: `Generated · ${(res.duration_ms / 1000).toFixed(1)}s`, ok: true });
    } catch (err) {
      setStatus({ text: (err as Error).message, ok: false });
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!projectId || !file) return;
    setBusy(true);
    setStatus(null);
    try {
      const res = await uploadVoiceover(projectId, file);
      setVoiceoverUrl(res.storage_path);
      setStatus({ text: "Audio uploaded", ok: true });
    } catch (err) {
      setStatus({ text: (err as Error).message, ok: false });
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  return (
    <div
      className="panel"
      style={{ padding: "14px 14px 16px", display: "flex", flexDirection: "column", gap: "10px" }}
    >
      {/* Title */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontSize: "10px", color: "var(--amber)" }}>♪</span>
        <span
          style={{
            fontSize: "11px",
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: "var(--text-2)",
            fontFamily: "var(--font-syne)",
          }}
        >
          Voiceover
        </span>
      </div>

      <input
        value={voice}
        onChange={(e) => setVoice(e.target.value)}
        placeholder="Voice name (e.g. Adam)"
        className="field"
        style={{ fontSize: "12px", padding: "8px 10px" }}
      />

      <textarea
        value={script}
        onChange={(e) => setScript(e.target.value)}
        placeholder="Enter narration script…"
        className="field"
        rows={3}
        style={{ fontSize: "12px", padding: "8px 10px", resize: "none", lineHeight: 1.5 }}
      />

      <div style={{ display: "flex", gap: "6px" }}>
        <button
          onClick={() => void handleGenerate()}
          disabled={busy || !script.trim()}
          className="btn-amber"
          style={{ flex: 1, fontSize: "11px", padding: "8px 10px" }}
        >
          {busy ? "Working…" : "Generate TTS"}
        </button>
        <label
          className="btn-outline"
          style={{ fontSize: "11px", padding: "8px 12px", cursor: "pointer" }}
        >
          Upload
          <input type="file" accept="audio/*" onChange={(e) => void handleUpload(e)} style={{ display: "none" }} />
        </label>
      </div>

      {status && (
        <p
          style={{
            fontSize: "11px",
            color: status.ok ? "#4ADE80" : "#F87171",
            margin: 0,
          }}
        >
          {status.ok ? "✓ " : "✗ "}{status.text}
        </p>
      )}
    </div>
  );
}
