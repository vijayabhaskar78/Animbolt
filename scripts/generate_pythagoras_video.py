"""
scripts/generate_pythagoras_video.py

End-to-end runner that exercises the full Cursor for 2D Animation stack:
  1. Loads secrets from the root .env
  2. Boots the FastAPI app against a local SQLite database
  3. Registers a user, creates a project
  4. Calls POST /api/v1/scenes/generate  (Groq → Kimi-K2 → Manim code)
  5. Runs the Celery preview task inline (real Manim render, no broker needed)
  6. Retries with a simpler prompt if the first render fails
  7. Calls POST /api/v1/compositions/{id}/export  (ffmpeg concat)
  8. Runs the export task inline
  9. Copies the finished video next to this script as
        pythagoras_theorem_YYYYMMDD_HHMMSS.mp4
 10. Opens the video with the OS default player

Run from the repo root:
    set PYTHONPATH=backend
    python scripts/generate_pythagoras_video.py
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── 0. Locate repo root and put backend/ on sys.path ────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent  # …/scripts
REPO_ROOT = SCRIPT_DIR.parent  # …/Cursor for 2D Animation
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── 1. Load .env secrets BEFORE any app imports ─────────────────────────────


def _load_env(path: Path) -> None:
    """Parse a .env file and export variables into os.environ (no-op if absent)."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            os.environ.setdefault(key, value)


_load_env(REPO_ROOT / ".env")


# ─── 2. Override settings for a fully local run ──────────────────────────────

ARTIFACTS_DIR = REPO_ROOT / "backend" / "artifacts" / "pythagoras_app"
DB_PATH = REPO_ROOT / "backend" / "pythagoras_app.db"

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["ARTIFACTS_DIR"] = str(ARTIFACTS_DIR)
os.environ["SIMULATE_RENDER"] = "false"  # use real Manim
os.environ["GROQ_MODEL"] = "moonshotai/kimi-k2-instruct-0905"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"  # not used inline

# Clean slate
if ARTIFACTS_DIR.exists():
    shutil.rmtree(ARTIFACTS_DIR)
if DB_PATH.exists():
    DB_PATH.unlink()


# ─── 3. Bootstrap the app (after env vars are set) ───────────────────────────

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db.base import Base  # noqa: E402
from app.db.session import configure_engine  # noqa: E402

engine, _ = configure_engine()
Base.metadata.create_all(bind=engine)

# Monkey-patch Celery + Redis so tasks run inline without a broker
import app.api.routes.compositions as _compositions_routes  # noqa: E402
import app.api.routes.scenes as _scenes_routes  # noqa: E402
import app.services.preview_events as _preview_events_mod  # noqa: E402
from app.workers import tasks as _tasks  # noqa: E402

_scenes_routes.celery_app.send_task = lambda *a, **kw: None
_compositions_routes.celery_app.send_task = lambda *a, **kw: None
_preview_events_mod.publish_preview_event = lambda *a, **kw: None  # type: ignore[assignment]

from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

settings = get_settings()

print(f"\n{'=' * 60}")
print(f"  Cursor for 2D Animation — Pythagoras Theorem Video")
print(f"{'=' * 60}")
print(f"  Groq model     : {settings.groq_model}")
print(
    f"  API key present: {'yes' if settings.groq_api_key else 'NO — will use fallback code'}"
)
print(f"  Artifacts dir  : {ARTIFACTS_DIR}")
print(f"  DB             : {DB_PATH}")
print(f"{'=' * 60}\n")


# ─── 4. Prompts ───────────────────────────────────────────────────────────────

PROMPT_PRIMARY = (
    "Create a short educational Manim animation explaining the Pythagorean theorem. "
    "Requirements: "
    "- Use only `from manim import *`. Do NOT import numpy or use np directly. "
    "- Define exactly ONE class named GeneratedScene(Scene). "
    "- Draw a right triangle using Polygon with explicit 3D numpy array coordinates, "
    "  e.g. Polygon(np.array([-3,-2,0]), np.array([1,-2,0]), np.array([-3,2,0])). "
    "- Use np.array for all coordinate vectors. "
    "- Label the three sides using Text: 'a' (vertical leg, blue), "
    "  'b' (horizontal leg, green), 'c' (hypotenuse, red). "
    "- Draw three filled squares on each side with matching colors, labeled a², b², c². "
    "- Finish with a large centered Text: 'a² + b² = c²'. "
    "- Keep all objects inside the visible frame. Total duration <= 10 s. "
    "- No MathTex, no Tex, no camera movement, no unsafe imports."
)

PROMPT_RETRY = (
    "Create a very simple, render-safe Manim animation for the Pythagorean theorem. "
    "Rules: only `from manim import *`, one GeneratedScene(Scene), "
    "no MathTex, no Tex, no camera movement, no numpy aliased as np. "
    "Use np.array() for coordinates. "
    "Show a right triangle (Polygon), three squares (Square) in blue, green, red, "
    "labels a, b, c on the sides with Text, labels a², b², c² on the squares with Text, "
    "and end with a big Text: 'a² + b² = c²' centered on screen. "
    "Use simple explicit coordinates. Keep everything in frame."
)

PROMPT_MINIMAL = (
    "Write the simplest possible GeneratedScene(Scene) Manim animation that shows: "
    "1) The words 'Pythagorean Theorem' at the top. "
    "2) A right triangle (Polygon, white). "
    "3) Side labels a, b, c using Text. "
    "4) The equation a² + b² = c² using Text at the bottom. "
    "Only use `from manim import *`. No MathTex, no Tex, no numpy alias, no camera moves."
)


# ─── 5. Helper ────────────────────────────────────────────────────────────────


def _first_asset(job_data: dict, asset_type: str) -> str | None:
    for asset in job_data.get("assets", []):
        if asset.get("asset_type") == asset_type:
            return asset.get("storage_path")
    return None


def _run_preview(job_id: str) -> tuple[bool, str]:
    """Run the preview render task inline. Returns (success, error)."""
    try:
        _tasks.render_preview_job.run(job_id)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _run_export(job_id: str) -> tuple[bool, str]:
    """Run the export composition task inline. Returns (success, error)."""
    try:
        _tasks.export_composition_job.run(job_id)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


# ─── 6. Main pipeline ─────────────────────────────────────────────────────────


def main() -> None:
    with TestClient(app) as client:
        # 6.1 Register user
        print("[1/7] Registering user …")
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "pythagoras@cursor2d.local", "password": "Password123!"},
        )
        if reg.status_code not in (201, 409):
            print(f"      FAILED: {reg.status_code} — {reg.text}")
            sys.exit(1)

        # If already registered (409), log in instead
        if reg.status_code == 409:
            login = client.post(
                "/api/v1/auth/login",
                json={"email": "pythagoras@cursor2d.local", "password": "Password123!"},
            )
            token = login.json()["access_token"]
        else:
            token = reg.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        print("      OK\n")

        # 6.2 Create project
        print("[2/7] Creating project …")
        proj = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "title": "Pythagorean Theorem",
                "description": "Auto-generated via scripts/generate_pythagoras_video.py",
            },
        )
        if proj.status_code != 201:
            print(f"      FAILED: {proj.status_code} — {proj.text}")
            sys.exit(1)
        project_id = proj.json()["id"]
        print(f"      project_id = {project_id}\n")

        # 6.3 Generate scene (with up to 3 prompt attempts)
        print(
            "[3/7] Generating Manim scene via Groq (moonshotai/kimi-k2-instruct-0905) …"
        )
        scene_id = None
        preview_job_id = None
        generation_payload = None
        generated_code = ""

        prompts = [PROMPT_PRIMARY, PROMPT_RETRY, PROMPT_MINIMAL]

        for attempt_idx, prompt in enumerate(prompts, start=1):
            print(f"      Prompt attempt {attempt_idx}/{len(prompts)} …")

            if scene_id is None:
                gen_resp = client.post(
                    "/api/v1/scenes/generate",
                    headers=headers,
                    json={
                        "project_id": project_id,
                        "prompt": prompt,
                        "style_preset": "educational",
                        "max_duration_sec": 10,
                        "aspect_ratio": "16:9",
                    },
                )
            else:
                gen_resp = client.post(
                    f"/api/v1/scenes/{scene_id}/regenerate",
                    headers=headers,
                    json={
                        "prompt": prompt,
                        "style_preset": "educational",
                        "max_duration_sec": 10,
                        "aspect_ratio": "16:9",
                    },
                )

            if gen_resp.status_code not in (200, 201):
                print(
                    f"      Generate FAILED: {gen_resp.status_code} — {gen_resp.text}"
                )
                sys.exit(1)

            generation_payload = gen_resp.json()
            scene_id = generation_payload["scene_id"]
            preview_job_id = generation_payload["preview_job_id"]
            validation = generation_payload["validation_status"]

            # Fetch the generated code
            proj_detail = client.get(f"/api/v1/projects/{project_id}", headers=headers)
            if proj_detail.status_code == 200:
                scenes_list = proj_detail.json().get("scenes", [])
                if scenes_list:
                    versions = scenes_list[0].get("versions", [])
                    if versions:
                        generated_code = versions[-1].get("manim_code", "")

            print(f"      Validation status : {validation}")
            if generated_code:
                print(f"      Code preview      : {generated_code[:120].strip()!r} …")

            # 6.4 Render preview
            print(f"\n[4/7] Rendering preview (attempt {attempt_idx}) …")
            ok, render_err = _run_preview(preview_job_id)

            # Check job status from DB
            job_resp = client.get(f"/api/v1/jobs/{preview_job_id}", headers=headers)
            preview_job = job_resp.json() if job_resp.status_code == 200 else {}
            job_status = preview_job.get("status", "unknown")
            job_err = preview_job.get("error_message", "")
            assets = preview_job.get("assets", [])

            print(f"      Render status     : {job_status}")
            if job_err:
                print(f"      Render error      : {job_err[:300]}")
            if not ok and render_err:
                print(f"      Task exception    : {render_err[:300]}")
            print(f"      Assets produced   : {[a['asset_type'] for a in assets]}")

            if job_status == "completed":
                print("      Render SUCCESS ✓\n")
                break

            print(
                f"      Render failed on attempt {attempt_idx}, retrying with simpler prompt …\n"
            )
        else:
            print("\nAll render attempts failed. Last generated code:")
            print(generated_code[:2000])
            sys.exit(1)

        # 6.5 Export composition
        print("[5/7] Queuing export composition …")
        export_resp = client.post(
            f"/api/v1/compositions/{project_id}/export",
            headers=headers,
            json={"title": "Pythagorean Theorem — Final Export"},
        )
        if export_resp.status_code != 202:
            print(f"      FAILED: {export_resp.status_code} — {export_resp.text}")
            sys.exit(1)
        export_job_id = export_resp.json()["job_id"]
        print(f"      export_job_id = {export_job_id}\n")

        # 6.6 Run export inline
        print("[6/7] Running export task (ffmpeg concat) …")
        ok_export, export_err = _run_export(export_job_id)

        exp_resp = client.get(f"/api/v1/jobs/{export_job_id}", headers=headers)
        export_job = exp_resp.json() if exp_resp.status_code == 200 else {}
        exp_status = export_job.get("status", "unknown")
        exp_err_msg = export_job.get("error_message", "")

        print(f"      Export status : {exp_status}")
        if exp_err_msg:
            print(f"      Export error  : {exp_err_msg[:300]}")
        if not ok_export and export_err:
            print(f"      Task exception: {export_err[:300]}")

        # 6.7 Locate output and copy to a friendly path
        print("\n[7/7] Locating output video …")

        # Try export first, then fall back to preview
        export_storage = _first_asset(export_job, "video_export")
        preview_storage = _first_asset(preview_job, "video_preview")

        chosen_storage = export_storage or preview_storage
        if not chosen_storage:
            print("      ERROR: no video asset found in either job")
            sys.exit(1)

        source_path = ARTIFACTS_DIR / chosen_storage
        asset_kind = "export" if export_storage else "preview"

        if not source_path.exists():
            print(f"      ERROR: expected video not found at {source_path}")
            sys.exit(1)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_name = f"pythagoras_theorem_{timestamp}.mp4"
        output_path = REPO_ROOT / output_name

        shutil.copy2(source_path, output_path)

        print(f"\n{'=' * 60}")
        print(f"  VIDEO GENERATED SUCCESSFULLY")
        print(f"{'=' * 60}")
        print(f"  Source asset  : {asset_kind} — {chosen_storage}")
        print(f"  Output file   : {output_path}")
        print(f"  File size     : {output_path.stat().st_size:,} bytes")
        print(f"  Groq model    : {settings.groq_model}")
        print(f"  Scene ID      : {scene_id}")
        print(f"{'=' * 60}\n")

        # Summary JSON for easy parsing
        summary = {
            "success": True,
            "output_video": str(output_path),
            "groq_model": settings.groq_model,
            "project_id": project_id,
            "scene_id": scene_id,
            "preview_job_id": preview_job_id,
            "export_job_id": export_job_id,
            "asset_kind": asset_kind,
            "validation_status": generation_payload["validation_status"],
            "generated_at": timestamp,
        }
        summary_path = REPO_ROOT / f"pythagoras_generation_summary_{timestamp}.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"  Summary JSON  : {summary_path}\n")

        # Open the video
        import subprocess

        try:
            if sys.platform == "win32":
                os.startfile(str(output_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(output_path)])
            else:
                subprocess.Popen(["xdg-open", str(output_path)])
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    main()
