"use client";

import { useState } from "react";
import { useProjectStore } from "@/store/useProjectStore";
import { exportComposition, getJob } from "@/lib/api";
import { assetUrl } from "@/lib/utils";

export default function ExportPanel() {
  const projectId = useProjectStore((s) => s.projectId);
  const exportSettings = useProjectStore((s) => s.exportSettings);
  const setExportSettings = useProjectStore((s) => s.setExportSettings);
  const exportProgress = useProjectStore((s) => s.exportProgress);
  const setExportProgress = useProjectStore((s) => s.setExportProgress);
  const scenes = useProjectStore((s) => s.scenes);

  const [busy, setBusy] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function handleExport() {
    if (!projectId) return;
    setBusy(true);
    setError("");
    setDownloadUrl(null);
    setExportProgress(0);
    try {
      const res = await exportComposition(projectId);
      const jobId = res.job_id;
      const poll = setInterval(async () => {
        try {
          const job = await getJob(jobId);
          if (job.status === "running") {
            setExportProgress(50);
          } else if (job.status === "completed") {
            clearInterval(poll);
            setExportProgress(100);
            setBusy(false);
            const asset = job.assets.find((a) => a.asset_type === "video_export");
            if (asset) setDownloadUrl(assetUrl(asset.storage_path));
          } else if (job.status === "failed") {
            clearInterval(poll);
            setBusy(false);
            setError(job.error_message || "Export failed");
          }
        } catch {
          clearInterval(poll);
          setBusy(false);
          setError("Failed to check export status");
        }
      }, 3000);
    } catch (err) {
      setBusy(false);
      setError((err as Error).message);
    }
  }

  return (
    <div
      className="panel"
      style={{ padding: "14px 14px 16px", display: "flex", flexDirection: "column", gap: "10px" }}
    >
      {/* Title */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
        <span style={{ fontSize: "10px", color: "var(--amber)" }}>↓</span>
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
          Export
        </span>
      </div>

      {/* Settings row */}
      <div style={{ display: "flex", gap: "6px" }}>
        <div style={{ flex: 1 }}>
          <div className="label" style={{ marginBottom: "4px" }}>Res</div>
          <select
            value={exportSettings.resolution}
            onChange={(e) => setExportSettings({ resolution: e.target.value as "720p" | "1080p" | "4K" })}
            className="field"
            style={{ fontSize: "11px", padding: "7px 8px" }}
          >
            <option value="720p">720p</option>
            <option value="1080p">1080p</option>
            <option value="4K">4K</option>
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <div className="label" style={{ marginBottom: "4px" }}>FPS</div>
          <select
            value={exportSettings.fps}
            onChange={(e) => setExportSettings({ fps: Number(e.target.value) as 30 | 60 })}
            className="field"
            style={{ fontSize: "11px", padding: "7px 8px" }}
          >
            <option value={30}>30</option>
            <option value={60}>60</option>
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <div className="label" style={{ marginBottom: "4px" }}>Format</div>
          <select value="mp4" className="field" disabled style={{ fontSize: "11px", padding: "7px 8px" }}>
            <option value="mp4">MP4</option>
          </select>
        </div>
      </div>

      {/* Export button */}
      <button
        onClick={() => void handleExport()}
        disabled={busy || scenes.length === 0}
        className="btn-amber"
        style={{ fontSize: "12px", padding: "9px" }}
      >
        {busy ? (
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
            Exporting…
          </>
        ) : (
          "Export Project"
        )}
      </button>

      {/* Progress */}
      {(busy || exportProgress > 0) && exportProgress < 100 && (
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${exportProgress}%` }} />
        </div>
      )}

      {error && (
        <p style={{ fontSize: "11px", color: "#F87171", margin: 0 }}>✗ {error}</p>
      )}

      {downloadUrl && (
        <a
          href={downloadUrl}
          target="_blank"
          rel="noreferrer"
          className="btn-outline"
          style={{ textAlign: "center", fontSize: "11px", textDecoration: "none", padding: "8px" }}
        >
          ↓ Download Video
        </a>
      )}
    </div>
  );
}
