"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/store/useProjectStore";
import { createProject } from "@/lib/api";

const EXAMPLES = [
  "Animate the Pythagorean theorem with glowing squares on each side of a right triangle",
  "Visualize a Fourier series decomposing a square wave step by step",
  "Show a 3Blue1Brown-style proof of the sum of angles in a triangle",
  "Animate how bubble sort works on an array of 8 colorful bars",
  "Draw the Mandelbrot set iteration by iteration with color gradients",
];

export default function HomePage() {
  const setProject = useProjectStore((s) => s.setProject);
  const router = useRouter();

  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [exampleIdx, setExampleIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setExampleIdx((i) => (i + 1) % EXAMPLES.length);
    }, 3500);
    return () => clearInterval(t);
  }, []);

  async function handleGo() {
    if (!prompt.trim()) return;
    setBusy(true);
    setTransitioning(true);
    try {
      const [p] = await Promise.all([
        createProject(prompt.trim().slice(0, 60), prompt.trim()),
        new Promise<void>((r) => setTimeout(r, 420)),
      ]);
      setProject(p.id, p.title);
      router.push(`/project/${p.id}/generate?prompt=${encodeURIComponent(prompt.trim())}`);
    } catch {
      setBusy(false);
      setTransitioning(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleGo();
  }

  return (
    <>
      {transitioning && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "var(--bg)",
            zIndex: 9999,
            animation: "fadeIn 0.38s ease forwards",
          }}
        />
      )}
      <main
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 24px",
          position: "relative",
          overflow: "hidden",
          background: "var(--bg)",
        }}
      >
        {/* Dot grid background */}
        <div
          className="hero-grid"
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.4,
            maskImage: "radial-gradient(ellipse 70% 70% at 50% 50%, black 0%, transparent 100%)",
            WebkitMaskImage: "radial-gradient(ellipse 70% 70% at 50% 50%, black 0%, transparent 100%)",
          }}
        />

        {/* Amber glow orb */}
        <div
          style={{
            position: "absolute",
            width: "600px",
            height: "600px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(245,158,11,0.06) 0%, transparent 70%)",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            pointerEvents: "none",
          }}
        />

        {/* Content */}
        <div
          style={{
            position: "relative",
            width: "100%",
            maxWidth: "620px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0",
          }}
        >
          {/* Eyebrow */}
          <div
            className="animate-fade-up"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              marginBottom: "20px",
            }}
          >
            <div
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "var(--amber)",
                boxShadow: "0 0 8px var(--amber)",
              }}
            />
            <span
              style={{
                fontSize: "11px",
                fontWeight: 600,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--text-2)",
              }}
            >
              AI Animation Studio
            </span>
          </div>

          {/* Wordmark */}
          <h1
            className="animate-fade-up-d1"
            style={{
              fontFamily: "var(--font-syne)",
              fontSize: "clamp(42px, 7vw, 72px)",
              fontWeight: 800,
              letterSpacing: "-0.035em",
              lineHeight: 1,
              textAlign: "center",
              margin: 0,
              marginBottom: "16px",
              color: "var(--text)",
            }}
          >
            Animate{" "}
            <span style={{ color: "var(--amber)" }}>anything</span>
            <br />
            with a prompt
          </h1>

          {/* Tagline */}
          <p
            className="animate-fade-up-d2"
            style={{
              fontSize: "15px",
              color: "var(--text-2)",
              textAlign: "center",
              lineHeight: 1.6,
              margin: 0,
              marginBottom: "36px",
              maxWidth: "440px",
            }}
          >
            Describe a mathematical concept or visual idea.
            <br />
            AnimBolt turns it into a Manim animation in seconds.
          </p>

          {/* Prompt area */}
          <div
            className="animate-fade-up-d3"
            style={{ width: "100%", marginBottom: "12px" }}
          >
            <div
              style={{
                position: "relative",
                borderRadius: "14px",
                border: "1px solid var(--border-mid)",
                background: "var(--surface)",
                transition: "border-color 0.2s, box-shadow 0.2s",
              }}
              onFocusCapture={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--amber)";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 0 0 3px var(--amber-10), 0 8px 40px rgba(245,158,11,0.08)";
              }}
              onBlurCapture={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "var(--border-mid)";
                (e.currentTarget as HTMLElement).style.boxShadow = "none";
              }}
            >
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={EXAMPLES[exampleIdx]}
                rows={4}
                style={{
                  width: "100%",
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  padding: "16px 18px",
                  paddingBottom: "56px",
                  color: "var(--text)",
                  fontSize: "14px",
                  fontFamily: "var(--font-dm-sans)",
                  lineHeight: 1.6,
                  resize: "none",
                  borderRadius: "14px",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  bottom: "12px",
                  left: "14px",
                  right: "14px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span
                  style={{
                    fontSize: "11px",
                    color: "var(--text-3)",
                  }}
                >
                  {prompt.length > 0 ? `${prompt.length} chars` : "⌘+Enter to generate"}
                </span>
                <button
                  onClick={() => void handleGo()}
                  disabled={busy || !prompt.trim()}
                  className="btn-amber"
                  style={{ padding: "7px 18px", fontSize: "12px" }}
                >
                  {busy ? (
                    <>
                      <span
                        style={{
                          width: "12px",
                          height: "12px",
                          border: "2px solid rgba(9,9,10,0.3)",
                          borderTopColor: "#09090A",
                          borderRadius: "50%",
                          animation: "spin 0.7s linear infinite",
                          display: "inline-block",
                        }}
                      />
                      Creating...
                    </>
                  ) : (
                    "Generate Animation →"
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Example chips */}
          <div
            className="animate-fade-up-d4"
            style={{
              display: "flex",
              gap: "6px",
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            {["Pythagorean theorem", "Fourier transform", "Bubble sort", "Mandelbrot set"].map((label) => (
              <button
                key={label}
                onClick={() => setPrompt(`Animate the ${label} step by step`)}
                style={{
                  padding: "5px 12px",
                  background: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: "999px",
                  color: "var(--text-2)",
                  fontSize: "11px",
                  cursor: "pointer",
                  transition: "all 0.15s",
                  fontFamily: "var(--font-dm-sans)",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--amber)";
                  (e.currentTarget as HTMLElement).style.color = "var(--amber)";
                  (e.currentTarget as HTMLElement).style.background = "var(--amber-10)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-2)";
                  (e.currentTarget as HTMLElement).style.background = "var(--card)";
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
