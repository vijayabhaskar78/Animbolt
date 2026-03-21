"""
Script to generate 10 test animations via the backend API and evaluate quality.
Run from: backend/ directory
Usage: python tests/generate_10_animations.py
"""
import json
import time
import sys
import httpx

BASE = "http://localhost:8000/api/v1"
EMAIL = "quality_test_v1@animbolt.local"
PASSWORD = "animbolt-quality-v1"

PROMPTS = [
    "Visualize the Pythagorean theorem with animated squares on each side of a right triangle",
    "Show how a derivative is the slope of a tangent line on a curve",
    "Animate the Fibonacci sequence as growing squares spiraling outward",
    "Show Euler's identity e^(i*pi) + 1 = 0 as a unit circle animation",
    "Visualize matrix multiplication as a linear transformation of space",
    "Show the unit circle and how sine and cosine are defined from the angle",
    "Animate the sum of an infinite geometric series converging to a finite value",
    "Visualize the Fourier series approximating a square wave with sine terms",
    "Show the relationship between circles and pi by unrolling a circle",
    "Animate the quadratic formula being derived by completing the square",
]

def register_or_login(client: httpx.Client) -> str:
    """Register (or login if exists) and return JWT token."""
    r = client.post(f"{BASE}/auth/register", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code in (200, 201):
        print(f"[AUTH] Registered new user: {EMAIL}")
        return r.json()["access_token"]
    # Try login
    r = client.post(f"{BASE}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        print(f"[AUTH] Logged in as: {EMAIL}")
        return r.json()["access_token"]
    raise RuntimeError(f"Auth failed: {r.status_code} {r.text}")


def create_project(client: httpx.Client, token: str) -> str:
    r = client.post(
        f"{BASE}/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Quality Test Animations", "description": "10 test prompts for quality evaluation"},
    )
    r.raise_for_status()
    proj_id = r.json()["id"]
    print(f"[PROJECT] Created: {proj_id}")
    return proj_id


def generate_scene(client: httpx.Client, token: str, project_id: str, prompt: str) -> dict:
    r = client.post(
        f"{BASE}/scenes/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "project_id": project_id,
            "prompt": prompt,
            "style_preset": "technical-clean",
            "max_duration_sec": 8,
            "aspect_ratio": "16:9",
        },
    )
    r.raise_for_status()
    return r.json()


def poll_job(client: httpx.Client, token: str, job_id: str, timeout: int = 120) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(
            f"{BASE}/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "unknown")
            if status in ("completed", "failed"):
                return data
        time.sleep(2)
    return {"status": "timeout", "job_id": job_id}


def check_artifact(artifacts_dir: str, job_id: str) -> dict:
    """Check the rendered MP4 file quality."""
    from pathlib import Path
    job_dir = Path(artifacts_dir) / job_id
    preview = job_dir / "preview.mp4"
    err_log = job_dir / "manim_error.log"

    result = {
        "job_id": job_id,
        "preview_exists": preview.exists(),
        "preview_size": preview.stat().st_size if preview.exists() else 0,
        "has_error_log": err_log.exists(),
        "error_summary": "",
    }

    if err_log.exists():
        content = err_log.read_text(encoding="utf-8", errors="replace")
        # Extract the key error line
        for line in content.split("\n"):
            if "Error" in line or "error" in line or "Traceback" in line:
                result["error_summary"] = line.strip()[:200]
                break

    # Check if it's a real Manim video vs ffmpeg placeholder
    if preview.exists() and preview.stat().st_size > 100:
        with preview.open("rb") as f:
            header = f.read(20)
        result["is_real_mp4"] = b"ftyp" in header
        # Check if it's the "Animation Preview" placeholder
        # The placeholder has specific ffmpeg-generated content
        result["is_placeholder"] = result["preview_size"] in (9598, 12026)
    else:
        result["is_real_mp4"] = False
        result["is_placeholder"] = True

    return result


def main() -> None:
    import os
    artifacts_dir = os.environ.get("ARTIFACTS_DIR", "./artifacts")

    results = []
    with httpx.Client(timeout=60) as client:
        token = register_or_login(client)
        project_id = create_project(client, token)

        for i, prompt in enumerate(PROMPTS, 1):
            print(f"\n[{i}/10] Generating: {prompt[:60]}...")
            try:
                scene_data = generate_scene(client, token, project_id, prompt)
                job_id = scene_data["preview_job_id"]
                scene_id = scene_data["scene_id"]
                validation = scene_data.get("validation_status", "unknown")
                print(f"  → scene={scene_id} job={job_id} validation={validation}")

                # Poll for completion
                job_result = poll_job(client, token, job_id, timeout=180)
                status = job_result.get("status", "unknown")
                error_msg = job_result.get("error_message", "")
                print(f"  → job status: {status}" + (f" | error: {error_msg[:100]}" if error_msg else ""))

                # Check artifact
                artifact = check_artifact(artifacts_dir, job_id)
                size = artifact["preview_size"]
                is_real = artifact["is_real_mp4"]
                is_ph = artifact["is_placeholder"]
                err_sum = artifact["error_summary"]

                quality = "REAL_MANIM" if (is_real and not is_ph) else "PLACEHOLDER"
                print(f"  → {quality}: {size} bytes" + (f" | manim_err: {err_sum[:80]}" if err_sum else ""))

                results.append({
                    "prompt": prompt,
                    "job_id": job_id,
                    "validation": validation,
                    "job_status": status,
                    "size": size,
                    "quality": quality,
                    "error": error_msg[:200] if error_msg else err_sum,
                })
            except Exception as exc:
                print(f"  → EXCEPTION: {exc}")
                results.append({
                    "prompt": prompt,
                    "job_id": "N/A",
                    "validation": "error",
                    "job_status": "exception",
                    "size": 0,
                    "quality": "FAILED",
                    "error": str(exc)[:200],
                })

    # Summary
    print("\n" + "="*70)
    print("QUALITY EVALUATION SUMMARY")
    print("="*70)
    real_count = sum(1 for r in results if r["quality"] == "REAL_MANIM")
    print(f"Real Manim videos: {real_count}/10")
    print(f"Placeholders: {10 - real_count}/10")
    print()
    for i, r in enumerate(results, 1):
        status_icon = "✓" if r["quality"] == "REAL_MANIM" else "✗"
        print(f"{status_icon} [{i:2d}] {r['quality']:12s} {r['size']:8d}B | {r['prompt'][:55]}")
        if r["error"]:
            print(f"         ERROR: {r['error'][:80]}")

    # Write results to file
    from pathlib import Path
    results_path = Path("artifacts/quality_test_results.json")
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nFull results written to: {results_path}")

    if real_count < 8:
        sys.exit(1)  # Signal quality failure


if __name__ == "__main__":
    main()
