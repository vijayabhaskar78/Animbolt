"use client";

import Link from "next/link";
import { useProjectStore } from "@/store/useProjectStore";

export default function Navbar() {
  const projectTitle = useProjectStore((s) => s.projectTitle);
  const projectId = useProjectStore((s) => s.projectId);

  return (
    <nav
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "52px",
        padding: "0 20px",
        background: "var(--bg)",
        borderBottom: "1px solid var(--border)",
        flexShrink: 0,
        position: "relative",
        zIndex: 50,
      }}
    >
      {/* Logo */}
      <Link href="/" style={{ textDecoration: "none" }}>
        <span
          style={{
            fontFamily: "var(--font-syne)",
            fontSize: "17px",
            fontWeight: 800,
            letterSpacing: "-0.02em",
            color: "var(--amber)",
          }}
        >
          ANIMBOLT
        </span>
      </Link>

      {/* Project breadcrumb */}
      {projectTitle && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            position: "absolute",
            left: "50%",
            transform: "translateX(-50%)",
          }}
        >
          <span style={{ color: "var(--text-3)", fontSize: "13px" }}>·</span>
          <span
            style={{
              fontFamily: "var(--font-dm-sans)",
              fontSize: "12px",
              fontWeight: 500,
              color: "var(--text-2)",
              maxWidth: "260px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {projectTitle}
          </span>
        </div>
      )}

      {/* Right nav — DISABLED: Generate + Editor buttons hidden, code retained for future re-enable */}
      <div style={{ display: "none" }}>
        {projectId && (
          <>
            <Link href={`/project/${projectId}/generate`} style={{ textDecoration: "none" }}>
              <button className="btn-ghost" style={{ fontSize: "12px" }}>
                Generate
              </button>
            </Link>
            <Link href={`/project/${projectId}/editor`} style={{ textDecoration: "none" }}>
              <button className="btn-ghost" style={{ fontSize: "12px" }}>
                Editor
              </button>
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
