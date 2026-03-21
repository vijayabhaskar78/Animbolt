"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import { createProject, deleteProject, listProjects } from "@/lib/api";
import type { Project } from "@/lib/types";

export default function Sidebar() {
  const setProject = useProjectStore((s) => s.setProject);
  const projectId = useProjectStore((s) => s.projectId);
  const router = useRouter();

  const [projects, setProjects] = useState<Project[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  useEffect(() => {
    void listProjects().then(setProjects).catch(() => {});
  }, []);

  async function handleCreate() {
    if (!title.trim()) return;
    setBusy(true);
    try {
      const p = await createProject(title.trim(), "");
      setProjects((prev) => [p, ...prev]);
      setProject(p.id, p.title);
      setShowNew(false);
      setTitle("");
      router.push(`/project/${p.id}/generate`);
    } catch {
      /* silent */
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(e: React.MouseEvent, p: Project) {
    e.stopPropagation();
    try {
      await deleteProject(p.id);
      setProjects((prev) => prev.filter((x) => x.id !== p.id));
      if (projectId === p.id) {
        setProject("", "");
        router.push("/");
      }
    } catch { /* silent */ }
  }

  function selectProject(p: Project) {
    setProject(p.id, p.title);
    router.push(`/project/${p.id}/generate`);
  }

  return (
    <aside
      style={{
        width: "220px",
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        background: "var(--bg)",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "14px 14px 10px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: showNew ? "10px" : 0,
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
            Projects
          </span>
          <button
            onClick={() => setShowNew(!showNew)}
            title="New project"
            style={{
              width: "22px",
              height: "22px",
              borderRadius: "6px",
              border: "1px solid var(--border-mid)",
              background: "transparent",
              color: "var(--text-2)",
              fontSize: "16px",
              lineHeight: 1,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.12s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = "var(--amber-10)";
              (e.currentTarget as HTMLElement).style.borderColor = "var(--amber)";
              (e.currentTarget as HTMLElement).style.color = "var(--amber)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.borderColor = "var(--border-mid)";
              (e.currentTarget as HTMLElement).style.color = "var(--text-2)";
            }}
          >
            +
          </button>
        </div>

        {showNew && (
          <div style={{ display: "flex", gap: "6px" }}>
            <input
              className="field"
              style={{ fontSize: "12px", padding: "7px 10px", flex: 1 }}
              placeholder="Project title…"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void handleCreate(); }}
              autoFocus
            />
            <button
              className="btn-amber"
              style={{ padding: "7px 10px", fontSize: "11px", flexShrink: 0 }}
              onClick={() => void handleCreate()}
              disabled={busy || !title.trim()}
            >
              {busy ? "…" : "Go"}
            </button>
          </div>
        )}
      </div>

      {/* Project list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px 8px",
          display: "flex",
          flexDirection: "column",
          gap: "2px",
        }}
      >
        {projects.length === 0 && (
          <p
            style={{
              fontSize: "11px",
              color: "var(--text-3)",
              textAlign: "center",
              padding: "20px 8px",
              lineHeight: 1.5,
            }}
          >
            No projects yet.
            <br />
            Start from the home screen.
          </p>
        )}
        {projects.map((p) => {
          const isActive = projectId === p.id;
          const isHov = hoveredId === p.id;
          return (
            <div
              key={p.id}
              onMouseEnter={() => setHoveredId(p.id)}
              onMouseLeave={() => setHoveredId(null)}
              style={{
                display: "flex",
                alignItems: "center",
                borderRadius: "8px",
                background: isActive ? "var(--amber-10)" : isHov ? "var(--card)" : "transparent",
                transition: "background 0.12s",
              }}
            >
              <button
                onClick={() => selectProject(p)}
                style={{
                  textAlign: "left",
                  padding: "8px 10px",
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  flex: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  minWidth: 0,
                }}
              >
                <div
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    flexShrink: 0,
                    background: isActive ? "var(--amber)" : "var(--text-3)",
                    boxShadow: isActive ? "0 0 6px var(--amber)" : "none",
                    transition: "all 0.15s",
                  }}
                />
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 500,
                    color: isActive ? "var(--amber)" : "var(--text-2)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    transition: "color 0.12s",
                  }}
                >
                  {p.title}
                </div>
              </button>
              <button
                onClick={(e) => void handleDelete(e, p)}
                title="Delete project"
                style={{
                  flexShrink: 0,
                  width: "26px",
                  height: "26px",
                  marginRight: "6px",
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "6px",
                  fontSize: "12px",
                  color: "var(--text-3)",
                  opacity: isHov ? 1 : 0,
                  transition: "opacity 0.12s, color 0.12s, background 0.12s",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.color = "#F87171";
                  (e.currentTarget as HTMLElement).style.background = "rgba(248,113,113,0.1)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.color = "var(--text-3)";
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                }}
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
