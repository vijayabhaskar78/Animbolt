# Disabled Features — AnimBolt

Features that are intentionally hidden from users but whose code remains intact and can be re-enabled.

---

## 1. Generate Page — Top Prompt Bar

**Status:** Hidden (`display: none`)
**File:** `frontend/src/app/project/[id]/generate/page.tsx`
**Component used:** `<PromptInput onGenerate={handleGenerate} loading={loading} />`

### What it does
A bar across the top of the generate page that lets the user type a new prompt and generate additional scenes from within the project. Supports style preset, duration, and aspect ratio selection.

### Why disabled
The current UX focuses on a single full-center video. Multi-scene generation from the generate page is not needed right now. The initial prompt comes from the landing page and auto-starts generation on arrival.

### How to re-enable
In `generate/page.tsx`, find the comment `{/* Prompt bar — DISABLED */}` and restore the outer wrapper styles:

```tsx
{/* Prompt bar */}
<div
  style={{
    padding: "12px 16px",
    borderBottom: "1px solid var(--border)",
    background: "var(--surface)",
    flexShrink: 0,
  }}
>
  <PromptInput onGenerate={handleGenerate} loading={loading} />
</div>
```

---

## 2. Generate Page — Scene List / Scene Grid

**Status:** Removed from UI (component still exists on disk)
**File:** `frontend/src/app/project/[id]/generate/page.tsx`
**Component:** `frontend/src/components/SceneList.tsx` + `frontend/src/components/SceneCard.tsx`

### What it does
A grid of scene cards showing each generated scene with its thumbnail, status badge, progress, and action buttons (Regenerate, Render HD, Refine). When no scenes exist it shows "No scenes yet. Describe your animation above and hit Generate."

### Why disabled
The app now generates one video per project (up to 60s). A multi-scene grid is overkill for the current workflow. The full-center video player replaced the grid.

### How to re-enable
1. Add `import SceneList from "@/components/SceneList";` back to `generate/page.tsx`.
2. Replace the center video column with:

```tsx
{/* Center: scene grid */}
<div style={{ flex: 1, overflowY: "auto" }}>
  <SceneList
    onRegenerate={handleRegenerate}
    onRenderHD={handleRenderHD}
    onRefine={handleRefine}
  />
</div>
```

3. Move `<VideoPreview />` back to the right column (380px) alongside the "Open in Editor" button and remove the inline refine panel.

---

## 3. Generate Page — Render HD Button (SceneCard)

**Status:** Accessible via `SceneList` (which is hidden — see item 2)
**File:** `frontend/src/components/SceneCard.tsx`
**Handler:** `handleRenderHD(sceneId)` in `generate/page.tsx`

### What it does
Triggers a high-definition Manim render job (full quality, not preview). The button appears in the scene card hover actions. Job is polled and scene status updates in real time.

### Why disabled
Depends on `SceneList` being visible (disabled above). The HD render API and backend logic are fully functional.

### How to re-enable
Re-enable `SceneList` (item 2 above). The Render HD button will be available inside `SceneCard`.

---

## 4. Generate Page — Sidebar on Landing Page

**Status:** Removed
**File:** `frontend/src/app/page.tsx`

### What it does
Shows the project list sidebar on the home/landing screen.

### Why disabled
The sidebar only makes sense after the user has navigated to a project. It cluttered the landing page hero layout.

### How to re-enable
Add back to `frontend/src/app/page.tsx`:
```tsx
import Sidebar from "@/components/Sidebar";
// In return:
<>
  <Sidebar />
  <main>...</main>
</>
```

---

## 5. Navbar — Generate & Editor Buttons

**Status:** Hidden (`display: none`)
**File:** `frontend/src/components/Navbar.tsx`

### What it does
Two ghost buttons in the top-right corner of the navbar, visible whenever a project is active (`projectId` is set). "Generate" links to `/project/:id/generate` and "Editor" links to `/project/:id/editor`. They allow quick navigation between the two views.

### Why disabled
Navigation is now handled by the sidebar. Having the buttons duplicated in the navbar adds clutter without adding value at this stage.

### How to re-enable
In `Navbar.tsx`, find the comment `{/* Right nav — DISABLED */}` and restore the outer wrapper's `display`:

```tsx
{/* Right nav */}
<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
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
```

---

---

## 6. Right Panel — Static Refine Textarea & Apply Feedback Button

**Status:** Replaced by AI chat panel (code removed from JSX, but `handleRefine` logic unchanged)
**File:** `frontend/src/app/project/[id]/generate/page.tsx`

### What it did
A static textarea labelled "Refine Animation" with an "Apply Feedback" button and a separate "Regenerate from Scratch" button. The user typed feedback and clicked Apply to call `handleRefine(sceneId, feedback)`.

### Why replaced
Replaced with a full conversational chat UI. The same `handleRefine` backend call is used under the hood — the chat panel just wraps it with message history, user/assistant bubbles, and a typing indicator so it feels like talking to an AI rather than filling in a form.

### How to restore the static panel
Replace the `{/* Right: AI chat panel */}` section in `generate/page.tsx` with:

```tsx
{/* Right: refine / re-prompt panel */}
<div style={{ width: "340px", flexShrink: 0, borderLeft: "1px solid var(--border)", background: "var(--surface)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
  {/* ... scene status header ... */}
  <div style={{ flex: 1, padding: "16px", display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto" }}>
    <textarea
      className="field"
      placeholder="Describe what needs to be fixed or improved…"
      value={refineFeedback}
      onChange={(e) => setRefineFeedback(e.target.value)}
      rows={7}
      style={{ resize: "none", lineHeight: 1.6, fontSize: "13px", flex: 1 }}
      disabled={!selectedScene || isBusy}
    />
    <button className="btn-amber" style={{ width: "100%" }}
      disabled={!refineFeedback.trim() || !selectedScene || isBusy}
      onClick={() => { if (selectedScene && refineFeedback.trim()) { void handleRefine(selectedScene.id, refineFeedback.trim()); setRefineFeedback(""); } }}
    >Apply Feedback</button>
    <button className="btn-outline" style={{ width: "100%" }}
      disabled={!selectedScene || isBusy}
      onClick={() => { if (selectedScene) void handleRegenerate(selectedScene.id); }}
    >Regenerate from Scratch</button>
  </div>
</div>
```

Also add back `const [refineFeedback, setRefineFeedback] = useState("");` to the component state.

---

---

## 7. VideoPreview — Scene Number Labels ("Scene 01")

**Status:** Hidden (comment placeholder left in JSX; info bar label removed)
**File:** `frontend/src/components/VideoPreview.tsx`

### What it did
Two places showed a scene number:
1. **Spinner state** — a sub-label `"Scene 01"` (zero-padded) beneath the "Writing Manim code…" / "Rendering preview…" text while the job was running.
2. **Info bar** (bottom strip) — `"Scene 01 — complete"` on the left side of the bar. The duration (`30s`) on the right was kept.

### Why disabled
The app now treats each project as a single animation — scene numbering is an implementation detail that shouldn't surface in the UI.

### How to re-enable

**Spinner label** — in `VideoPreview.tsx`, replace the comment with:
```tsx
<p style={{ fontSize: "12px", margin: 0, color: "var(--text-3)" }}>
  Scene {String(selectedScene.sceneNumber).padStart(2, "0")}
</p>
```

**Info bar label** — restore `justifyContent: "space-between"` and add back the left span:
```tsx
<span style={{ fontSize: "11px", color: "var(--text-3)" }}>
  {selectedScene
    ? `Scene ${String(selectedScene.sceneNumber).padStart(2, "0")} — ${selectedScene.status}`
    : "No scene selected"}
</span>
```

---

---

## 8. Chat Panel — Regenerate from Scratch Button

**Status:** Hidden (`display: none`), code retained
**File:** `frontend/src/app/project/[id]/generate/page.tsx`

### What it did
A button in the footer of the right-side chat panel. When clicked, it called `handleRegenerate(selectedScene.id)` — discarding the existing Manim code and generating a completely new animation from the original prompt.

### Why disabled
The chat refine flow covers most correction needs. A full "nuke and restart" button is too destructive for the current single-animation UX.

### How to re-enable
In `generate/page.tsx`, find the comment `{/* Regenerate from Scratch — DISABLED */}` and remove the outer `<div style={{ display: "none" }}>` wrapper, leaving just the `<button>` inside.

---

## 9. Open in Editor Button — Navigation Disabled (Coming Soon shown instead)

**Status:** Button visible, navigation disabled — clicking shows a "Coming Soon" modal
**File:** `frontend/src/app/project/[id]/generate/page.tsx`

### What it did
Navigated to `/project/:id/editor` — the full timeline code editor for the project.

### Why changed
The editor page exists but is not ready for users. Rather than hiding the button, it now shows a polished "Coming Soon" modal with an animated orbital graphic so users know it's on the roadmap.

### How to fully re-enable
In `generate/page.tsx`, change the "Open in Editor" button's `onClick` from `setShowComingSoon(true)` back to:
```tsx
onClick={() => router.push(`/project/${params.id}/editor`)}
```
The `showComingSoon` state and modal JSX can then be deleted.

---

## Notes

- All backend routes, Celery tasks, and DB models for all features above are **fully functional** — nothing was removed from the backend.
- The `PromptInput`, `SceneList`, `SceneCard`, `VideoPreview` components are **all intact on disk**.
- Re-enabling any feature above requires only frontend changes.
