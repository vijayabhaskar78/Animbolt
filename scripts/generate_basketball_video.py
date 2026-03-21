"""
scripts/generate_basketball_video.py

End-to-end runner using the Cursor for 2D Animation application stack:
  1.  Load secrets from root .env
  2.  Boot FastAPI app against local SQLite (no Docker/Postgres needed)
  3.  Register user, create project  via  POST /api/v1/auth/register
                                          POST /api/v1/projects
  4.  Generate Manim scene via Groq   via  POST /api/v1/scenes/generate
      (model: moonshotai/kimi-k2-instruct-0905)
  5.  Run Celery preview task inline (real Manim render, no broker)
  6.  Retry with simpler prompts if render fails (up to 3 attempts)
  7.  Analyse AI-generated code and print every improvement found
  8.  Render the hand-crafted improved scene with real Manim
  9.  Export composition via            POST /api/v1/compositions/{id}/export
 10.  Copy final video to repo root and open with system player

Run from the repo root:
    set PYTHONPATH=backend
    python scripts/generate_basketball_video.py
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 0.  Repo layout
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent        # …/scripts
REPO_ROOT  = SCRIPT_DIR.parent                      # …/Cursor for 2D Animation
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# 1.  Load .env BEFORE any app import
# ---------------------------------------------------------------------------
def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key   = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


_load_env(REPO_ROOT / ".env")


# ---------------------------------------------------------------------------
# 2.  Override settings for fully local / broker-free run
# ---------------------------------------------------------------------------
ARTIFACTS_DIR = REPO_ROOT / "backend" / "artifacts" / "basketball_app"
DB_PATH       = REPO_ROOT / "backend" / "basketball_app.db"

os.environ["DATABASE_URL"]    = "sqlite:///" + DB_PATH.as_posix()
os.environ["ARTIFACTS_DIR"]   = str(ARTIFACTS_DIR)
os.environ["SIMULATE_RENDER"] = "false"
os.environ["GROQ_MODEL"]      = "moonshotai/kimi-k2-instruct-0905"
os.environ["REDIS_URL"]       = "redis://localhost:6379/0"

if ARTIFACTS_DIR.exists():
    shutil.rmtree(ARTIFACTS_DIR)
if DB_PATH.exists():
    DB_PATH.unlink()


# ---------------------------------------------------------------------------
# 3.  Bootstrap app  (env vars must be set first)
# ---------------------------------------------------------------------------
from app.core.config import get_settings                           # noqa: E402
get_settings.cache_clear()

from app.db.base    import Base                                    # noqa: E402
from app.db.session import configure_engine                        # noqa: E402
engine, _ = configure_engine()
Base.metadata.create_all(bind=engine)

import app.api.routes.compositions as _comp_routes                # noqa: E402
import app.api.routes.scenes       as _scene_routes               # noqa: E402
import app.services.preview_events as _preview_mod                # noqa: E402
from app.workers import tasks as _tasks                            # noqa: E402

_scene_routes.celery_app.send_task = lambda *a, **kw: None
_comp_routes.celery_app.send_task  = lambda *a, **kw: None
_preview_mod.publish_preview_event = lambda *a, **kw: None        # type: ignore[assignment]

from app.main import app                                           # noqa: E402
from fastapi.testclient import TestClient                          # noqa: E402

settings = get_settings()
SEP = "=" * 66

print()
print(SEP)
print("  Cursor for 2D Animation  —  Basketball Scene Generator")
print(SEP)
print("  Groq model     :", settings.groq_model)
print("  API key        :", "present" if settings.groq_api_key else "MISSING (fallback code)")
print("  Artifacts dir  :", ARTIFACTS_DIR)
print("  DB             :", DB_PATH)
print(SEP)
print()


# ---------------------------------------------------------------------------
# 4.  Prompts  (tried in order; stop at first successful render)
# ---------------------------------------------------------------------------
PROMPT_PRIMARY = (
    "Create a Manim Community Edition animation of a basketball scene. "
    "STRICT RULES: Only 'from manim import *'. No extra imports. "
    "Use np.array() for every coordinate vector. "
    "Exactly one class named GeneratedScene(Scene). "
    "No MathTex, no Tex, no camera movement. All objects inside the frame. Duration <= 10 s. "
    "Scene layout left to right: "
    "(1) STICK FIGURE person on the LEFT at x = -4.5: "
    "head = Circle(radius=0.28, color=YELLOW, fill_opacity=1) at np.array([-4.5, 1.5, 0]); "
    "torso = Line from head bottom down 1.1 units; "
    "two arm Lines from upper torso (left arm forward toward ball, right arm back); "
    "two upper-leg Lines from hip in mid-stride pose; "
    "two lower-leg Lines continuing to floor level. "
    "(2) BASKETBALL near the player left hand: "
    "Circle(radius=0.24, color=ORANGE, fill_opacity=1). "
    "Bounce it DOWN to near the floor and back UP exactly TWICE using animate.move_to(). "
    "(3) BASKETBALL HOOP on the RIGHT at x = +4.8: "
    "Rectangle backboard (white, width=0.22, height=1.6); "
    "horizontal rim Line (color=ORANGE, stroke_width=6) protruding left from backboard; "
    "3 short net Lines hanging below the rim in WHITE. "
    "(4) SHOT: animate ball along ArcBetweenPoints from hand position to rim centre "
    "using MoveAlongPath, then Flash(ball, color=ORANGE), then FadeOut(ball). "
    "(5) TEXT: Write(Text('Basketball!', color=ORANGE, font_size=42)) at top at start; "
    "Write(Text('SCORE!', color=YELLOW, font_size=64, weight=BOLD)) centred on screen at end."
)

PROMPT_RETRY_1 = (
    "Write a render-safe Manim GeneratedScene(Scene) animation of a basketball moment. "
    "Only 'from manim import *'. No MathTex. No Tex. No camera movement. One class only. "
    "Use np.array() for every coordinate. Keep all objects inside the visible frame. "
    "Step 1: head = Circle(radius=0.25, color=YELLOW, fill_opacity=1); "
    "head.move_to(np.array([-4.5, 1.5, 0])). "
    "body = Line(head.get_bottom(), head.get_bottom() + DOWN*1.1, color=WHITE, stroke_width=4). "
    "left_arm = Line(body.get_start()+DOWN*0.25, body.get_start()+DOWN*0.25+RIGHT*0.6+DOWN*0.35, color=WHITE, stroke_width=3). "
    "right_arm = Line(body.get_start()+DOWN*0.25, body.get_start()+DOWN*0.25+LEFT*0.5+DOWN*0.3, color=WHITE, stroke_width=3). "
    "left_leg = Line(body.get_end(), body.get_end()+RIGHT*0.55+DOWN*0.9, color=WHITE, stroke_width=4). "
    "right_leg = Line(body.get_end(), body.get_end()+LEFT*0.4+DOWN*0.9, color=WHITE, stroke_width=4). "
    "Step 2: ball = Circle(radius=0.24, color=ORANGE, fill_opacity=1); "
    "ball.move_to(np.array([-3.8, 0.9, 0])). "
    "Bounce: self.play(ball.animate.move_to(np.array([-3.8, -2.5, 0])), run_time=0.25); "
    "self.play(ball.animate.move_to(np.array([-3.8, 0.9, 0])), run_time=0.25). Repeat once. "
    "Step 3: backboard = Rectangle(width=0.22, height=1.6, color=WHITE, fill_opacity=0.9); "
    "backboard.move_to(np.array([5.1, 0.9, 0])). "
    "rim = Line(np.array([4.2, 0.35, 0]), np.array([5.0, 0.35, 0]), color=ORANGE, stroke_width=6). "
    "net1 = Line(np.array([4.3, 0.35, 0]), np.array([4.4, -0.2, 0]), color=WHITE, stroke_width=2). "
    "net2 = Line(np.array([4.6, 0.35, 0]), np.array([4.6, -0.2, 0]), color=WHITE, stroke_width=2). "
    "net3 = Line(np.array([4.9, 0.35, 0]), np.array([4.8, -0.2, 0]), color=WHITE, stroke_width=2). "
    "Step 4: arc = ArcBetweenPoints(ball.get_center(), np.array([4.6, 0.35, 0]), angle=-(TAU/5)); "
    "self.play(MoveAlongPath(ball, arc), run_time=1.5); "
    "self.play(Flash(ball, color=ORANGE), run_time=0.4); self.play(FadeOut(ball)). "
    "Step 5: score = Text('SCORE!', font_size=60, color=YELLOW, weight=BOLD); "
    "score.move_to(ORIGIN); self.play(Write(score)); self.wait(1)."
)

PROMPT_RETRY_2 = (
    "Write the simplest possible GeneratedScene(Scene) Manim animation showing basketball. "
    "Only 'from manim import *'. No MathTex, no Tex, no camera moves. One class. "
    "Draw: yellow Circle head + white Lines body/arms/legs on the left. "
    "Orange Circle ball that moves DOWN then UP once. "
    "White Rectangle backboard and orange Line rim on the right. "
    "ball.animate.move_to(RIGHT*5 + UP*0.35) to shoot. "
    "Flash(ball, color=ORANGE). FadeOut(ball). "
    "Text 'SCORE!' in YELLOW at ORIGIN at the end. "
    "Keep everything inside the frame. Total <= 10 s."
)


# ---------------------------------------------------------------------------
# 5.  Helpers
# ---------------------------------------------------------------------------
def _first_asset(job_data: dict, asset_type: str):
    for asset in job_data.get("assets", []):
        if asset.get("asset_type") == asset_type:
            return asset.get("storage_path")
    return None


def _run_preview(job_id: str):
    try:
        _tasks.render_preview_job.run(job_id)
        return True, ""
    except Exception as exc:           # noqa: BLE001
        return False, str(exc)


def _run_export(job_id: str):
    try:
        _tasks.export_composition_job.run(job_id)
        return True, ""
    except Exception as exc:           # noqa: BLE001
        return False, str(exc)


# ---------------------------------------------------------------------------
# 6.  Code analyser  — scans AI output and returns list of issues
# ---------------------------------------------------------------------------
def analyse_code(code: str) -> list:
    issues = []
    c = code.lower()

    # Visual elements
    if "circle" not in c:
        issues.append(
            "[MISSING BALL] No Circle — the basketball itself is absent. "
            "Fix: ball = Circle(radius=0.24, color=ORANGE, fill_opacity=1)"
        )
    if "rectangle" not in c:
        issues.append(
            "[MISSING BACKBOARD] No Rectangle for the backboard. "
            "Fix: Rectangle(width=0.22, height=1.6, color=WHITE, fill_opacity=0.9) on the right."
        )
    if "rim" not in c:
        issues.append(
            "[MISSING RIM] No rim drawn. "
            "Fix: short horizontal Line(color=ORANGE, stroke_width=6) for the rim."
        )
    if "net" not in c:
        issues.append(
            "[MISSING NET] No net lines below the rim. "
            "Fix: 3 short diagonal Lines hanging from the rim in WHITE."
        )

    # Stick figure completeness
    for part in ("head", "body", "arm", "leg"):
        if part not in c:
            issues.append(
                "[INCOMPLETE FIGURE] Stick figure missing part: '{}'. "
                "Fix: add {} Line/Circle to complete the running person.".format(part, part)
            )

    # Animation quality
    bounce_downs = c.count("shift(down") + c.count("move_to") if "down" in c else 0
    if c.count("shift(down") < 2 and c.count("run_time=0.2") < 2 and "bounce" not in c:
        issues.append(
            "[NO DRIBBLE] Ball bounces fewer than 2 times. "
            "Fix: add 2 pairs of DOWN+UP animate.move_to() calls with run_time=0.25."
        )
    if "movealongpath" not in c and "arcbetweenpoints" not in c:
        issues.append(
            "[NO ARC SHOT] Ball does not travel a curved arc to the hoop. "
            "Fix: ArcBetweenPoints(start, end, angle=-(TAU/5)) + MoveAlongPath(ball, arc)."
        )
    if "flash" not in c and "indicate" not in c:
        issues.append(
            "[NO IMPACT FX] No Flash or Indicate when ball enters hoop. "
            "Fix: self.play(Flash(ball, color=ORANGE)) on scoring."
        )
    if "score" not in c and "goal" not in c:
        issues.append(
            "[NO SCORE TEXT] No SCORE/GOAL text at the end. "
            "Fix: self.play(Write(Text('SCORE!', color=YELLOW, font_size=64)))."
        )
    if "basketball" not in c:
        issues.append(
            "[NO TITLE] No 'Basketball' title text. "
            "Fix: Write(Text('Basketball!', color=ORANGE, font_size=42)) at the top."
        )

    # Pacing
    rt_count = c.count("run_time")
    if rt_count < 4:
        issues.append(
            "[POOR PACING] Only {} run_time arguments found. "
            "Fix: add explicit run_time=... to every self.play() call "
            "(0.25–1.6 s) for smooth, natural motion.".format(rt_count)
        )
    wait_count = c.count("self.wait(")
    if wait_count < 2:
        issues.append(
            "[NO PAUSES] Only {} self.wait() calls. "
            "Fix: add self.wait(0.3) between major beats so the "
            "viewer can follow the action.".format(wait_count)
        )

    # Safety
    if "mathtex" in c:
        issues.append(
            "[SAFETY] MathTex detected — LaTeX is not guaranteed and will crash. "
            "Fix: replace every MathTex(...) with Text(...)."
        )
    if "camera.frame.animate" in c:
        issues.append(
            "[SAFETY] camera.frame.animate on a plain Scene crashes. "
            "Fix: remove camera movement or subclass MovingCameraScene."
        )

    # Layout
    if not any(kw in c for kw in ("to_edge", "move_to", "shift", "next_to")):
        issues.append(
            "[LAYOUT] No explicit positioning — all objects default to ORIGIN "
            "and overlap. Fix: use .move_to(), .shift(), or .to_edge() on every object."
        )

    # Seams / realism
    if "arc(" not in c and "seam" not in c:
        issues.append(
            "[REALISM] Basketball has no seam arcs. "
            "Fix: add two Arc() objects on the ball for classic seam lines."
        )

    return issues


def print_analysis(issues: list, code: str) -> None:
    print()
    print(SEP)
    print("  IMPROVEMENT ANALYSIS  —  Raw AI-Generated Code")
    print(SEP)
    if not issues:
        print("  No critical issues found — AI output looks solid!")
        print()
        return
    print("  Found {} issue(s) in the AI output:\n".format(len(issues)))
    for i, issue in enumerate(issues, 1):
        end = issue.index("]")
        tag    = issue[: end + 1]
        detail = issue[end + 1 :].strip()
        print("  {:02d}. {}".format(i, tag))
        # Word-wrap detail at ~60 chars
        words = detail.split()
        line  = "       "
        for w in words:
            if len(line) + len(w) + 1 > 68:
                print(line)
                line = "       " + w
            else:
                line = line + " " + w if line.strip() else "       " + w
        if line.strip():
            print(line)
        print()
    print(SEP)
    print()


# ---------------------------------------------------------------------------
# 7.  Improved Manim code  (hand-crafted, fixes every issue above)
# ---------------------------------------------------------------------------
IMPROVED_CODE = (
    '"""'
    "\n"
    "Basketball Animation  —  Improved Scene\n"
    "Fixes applied over raw AI output:\n"
    "  01  Stick figure: head + torso + 2 arms + 2 upper legs + 2 lower legs (running)\n"
    "  02  Basketball seam arcs added for visual realism\n"
    "  03  Dribble: 2x DOWN->UP bounce with rush_into/rush_from easing\n"
    "  04  Hoop: pole + white backboard + orange rim + 3 net lines\n"
    "  05  Arc shot: ArcBetweenPoints + MoveAlongPath (curved trajectory)\n"
    "  06  Flash(ball, ORANGE) + Indicate(rim) on scoring\n"
    "  07  run_time tuned per step (0.22 – 1.6 s) throughout\n"
    "  08  self.wait() pauses between every major beat\n"
    "  09  Title 'Basketball!' at top from frame 1\n"
    "  10  'SCORE!' with Write + Indicate at the very end\n"
    "  11  All objects explicitly positioned — nothing overlaps at ORIGIN\n"
    "  12  No MathTex / Tex / camera.frame.animate — fully render-safe\n"
    "  13  Dark background #1a1a2e for strong visual contrast\n"
    '"""'
    "\n"
    "from manim import *\n"
    "\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        self.camera.background_color = '#1a1a2e'\n"
    "\n"
    "        # ── TITLE ────────────────────────────────────────────────────────\n"
    "        title = Text('Basketball!', font_size=42, color=ORANGE, weight=BOLD)\n"
    "        title.to_edge(UP, buff=0.25)\n"
    "        self.play(Write(title), run_time=0.8)\n"
    "\n"
    "        # ── FLOOR ────────────────────────────────────────────────────────\n"
    "        floor_y = -2.8\n"
    "        floor = Line(\n"
    "            np.array([-7.2, floor_y, 0]),\n"
    "            np.array([ 7.2, floor_y, 0]),\n"
    "            color=GRAY_C, stroke_width=2,\n"
    "        )\n"
    "        self.play(Create(floor), run_time=0.4)\n"
    "\n"
    "        # ── STICK FIGURE ─────────────────────────────────────────────────\n"
    "        px      = -4.5\n"
    "        head_c  = np.array([px, floor_y + 3.30, 0])\n"
    "        shldr_y = head_c[1] - 0.28\n"
    "        hip_y   = shldr_y  - 1.10\n"
    "\n"
    "        head = Circle(radius=0.28, color=YELLOW, fill_opacity=1, stroke_width=0)\n"
    "        head.move_to(head_c)\n"
    "\n"
    "        torso = Line(np.array([px, shldr_y, 0]),\n"
    "                     np.array([px, hip_y,   0]),\n"
    "                     color=WHITE, stroke_width=4)\n"
    "\n"
    "        arm_root = np.array([px, shldr_y - 0.25, 0])\n"
    "        l_arm = Line(arm_root,\n"
    "                     np.array([px + 0.65, shldr_y - 0.80, 0]),\n"
    "                     color=WHITE, stroke_width=3)\n"
    "        r_arm = Line(arm_root,\n"
    "                     np.array([px - 0.50, shldr_y - 0.65, 0]),\n"
    "                     color=WHITE, stroke_width=3)\n"
    "\n"
    "        hip_pt  = np.array([px, hip_y, 0])\n"
    "        l_knee  = np.array([px + 0.55, floor_y + 0.90, 0])\n"
    "        r_knee  = np.array([px - 0.40, floor_y + 0.80, 0])\n"
    "\n"
    "        l_upper = Line(hip_pt, l_knee, color=WHITE, stroke_width=4)\n"
    "        l_lower = Line(l_knee, np.array([px + 0.90, floor_y + 0.20, 0]),\n"
    "                       color=WHITE, stroke_width=3)\n"
    "        r_upper = Line(hip_pt, r_knee, color=WHITE, stroke_width=4)\n"
    "        r_lower = Line(r_knee, np.array([px - 0.05, floor_y + 0.10, 0]),\n"
    "                       color=WHITE, stroke_width=3)\n"
    "\n"
    "        person = VGroup(head, torso, l_arm, r_arm,\n"
    "                        l_upper, l_lower, r_upper, r_lower)\n"
    "        self.play(FadeIn(person), run_time=0.8)\n"
    "\n"
    "        # ── BASKETBALL ───────────────────────────────────────────────────\n"
    "        ball_pos = np.array([px + 0.65, shldr_y - 0.80 + 0.22, 0])\n"
    "        ball = Circle(radius=0.24, color=ORANGE, fill_opacity=1, stroke_width=0)\n"
    "        ball.move_to(ball_pos)\n"
    "        seam1 = Arc(radius=0.24, start_angle=PI / 6, angle=2 * PI / 3,\n"
    "                    color=DARK_BROWN, stroke_width=2).move_to(ball_pos)\n"
    "        seam2 = Arc(radius=0.24, start_angle=-PI / 2, angle=PI,\n"
    "                    color=DARK_BROWN, stroke_width=2).move_to(ball_pos)\n"
    "        basketball = VGroup(ball, seam1, seam2)\n"
    "        self.play(FadeIn(basketball), run_time=0.5)\n"
    "        self.wait(0.3)\n"
    "\n"
    "        # ── DRIBBLE  (2 bounces) ─────────────────────────────────────────\n"
    "        ground_pos = np.array([ball_pos[0], floor_y + 0.25, 0])\n"
    "        for _ in range(2):\n"
    "            self.play(basketball.animate.move_to(ground_pos),\n"
    "                      run_time=0.22, rate_func=rush_into)\n"
    "            self.play(basketball.animate.move_to(ball_pos),\n"
    "                      run_time=0.22, rate_func=rush_from)\n"
    "        self.wait(0.3)\n"
    "\n"
    "        # ── HOOP ─────────────────────────────────────────────────────────\n"
    "        hx     = 4.8\n"
    "        rim_y  = 0.35\n"
    "        rim_lx = hx - 0.90\n"
    "        rim_rx = hx + 0.05\n"
    "\n"
    "        pole = Line(np.array([hx + 0.15, floor_y, 0]),\n"
    "                    np.array([hx + 0.15, rim_y - 0.25, 0]),\n"
    "                    color=GRAY, stroke_width=6)\n"
    "\n"
    "        backboard = Rectangle(width=0.22, height=1.65,\n"
    "                              color=WHITE, fill_opacity=0.88)\n"
    "        backboard.move_to(np.array([hx + 0.26, rim_y + 0.45, 0]))\n"
    "\n"
    "        rim = Line(np.array([rim_lx, rim_y, 0]),\n"
    "                   np.array([rim_rx, rim_y, 0]),\n"
    "                   color=ORANGE, stroke_width=6)\n"
    "\n"
    "        net_xs = [rim_lx + 0.10, rim_lx + 0.48, rim_lx + 0.80]\n"
    "        net_lines = VGroup(*[\n"
    "            Line(np.array([x, rim_y, 0]),\n"
    "                 np.array([x + 0.12, rim_y - 0.55, 0]),\n"
    "                 color=WHITE, stroke_width=1.5)\n"
    "            for x in net_xs\n"
    "        ])\n"
    "\n"
    "        hoop = VGroup(pole, backboard, rim, net_lines)\n"
    "        self.play(FadeIn(hoop), run_time=0.8)\n"
    "        self.wait(0.2)\n"
    "\n"
    "        # ── SHOT ARC ─────────────────────────────────────────────────────\n"
    "        rim_target = np.array([(rim_lx + rim_rx) / 2, rim_y, 0])\n"
    "        arc = ArcBetweenPoints(ball_pos, rim_target, angle=-(TAU / 5))\n"
    "        self.play(MoveAlongPath(basketball, arc),\n"
    "                  run_time=1.6, rate_func=linear)\n"
    "\n"
    "        # ── IMPACT EFFECTS ───────────────────────────────────────────────\n"
    "        self.play(Flash(ball, color=ORANGE, line_length=0.32, num_lines=12),\n"
    "                  run_time=0.45)\n"
    "        self.play(Indicate(rim, color=YELLOW, scale_factor=1.30), run_time=0.40)\n"
    "        self.play(FadeOut(basketball), run_time=0.35)\n"
    "        self.wait(0.25)\n"
    "\n"
    "        # ── SCORE TEXT ───────────────────────────────────────────────────\n"
    "        score = Text('SCORE!', font_size=72, color=YELLOW, weight=BOLD)\n"
    "        score.move_to(ORIGIN)\n"
    "        self.play(Write(score), run_time=0.8)\n"
    "        self.play(Indicate(score, scale_factor=1.15), run_time=0.5)\n"
    "        self.wait(1.5)\n"
    "\n"
    "        # ── FADE OUT ─────────────────────────────────────────────────────\n"
    "        self.play(FadeOut(VGroup(title, floor, person, hoop, score)),\n"
    "                  run_time=1.0)\n"
    "        self.wait(0.3)\n"
)


def render_improved(timestamp: str) -> Path:
    improved_py = REPO_ROOT / "basketball_scene.
