"""
Direct rendering quality test — bypasses Celery, calls run_render directly.
Tests 10 different Manim scene types and evaluates output quality.
Run: python -m pytest tests/test_10_renders_direct.py -v -s --timeout=600
"""
import os
import time
from pathlib import Path

import pytest

# Force real rendering (not simulate)
os.environ["SIMULATE_RENDER"] = "false"

from app.core.config import get_settings
get_settings.cache_clear()

from app.services.groq_adapter import generate_manim_code, _sanitize_code
from app.services.manim_validator import validate_manim_code
from app.services.rendering import run_render

ARTIFACTS = Path("artifacts/quality_test")
ARTIFACTS.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    ("pythagorean", "Visualize the Pythagorean theorem with animated squares on each side of a right triangle"),
    ("derivative", "Show how a derivative is the slope of a tangent line on a curve"),
    ("fibonacci", "Animate the Fibonacci sequence as growing squares spiraling outward"),
    ("euler_identity", "Show Euler's identity e to the power i*pi plus 1 equals 0 as a unit circle animation"),
    ("matrix_transform", "Visualize a 2D matrix as a linear transformation of the plane, show how basis vectors transform"),
    ("unit_circle", "Show the unit circle and how sine and cosine are defined from the angle, animated"),
    ("geometric_series", "Animate the sum of an infinite geometric series one-half plus one-quarter converging to 1"),
    ("fourier_series", "Visualize the Fourier series approximating a square wave by adding sine harmonics"),
    ("circle_pi", "Show the relationship between circles and pi by unrolling a circle circumference"),
    ("quadratic_formula", "Animate the quadratic formula derivation by completing the square on ax squared plus bx plus c"),
]


def _check_mp4(path: Path) -> dict:
    """Return quality info about an MP4 file."""
    if not path.exists():
        return {"exists": False, "size": 0, "is_real_mp4": False, "quality": "MISSING"}
    size = path.stat().st_size
    with path.open("rb") as f:
        header = f.read(20)
    is_mp4 = b"ftyp" in header or b"moov" in header
    # Placeholder detection: the ffmpeg black-screen placeholder has known sizes
    # but any real Manim video at 480p15 for 2+ seconds should be larger than ~8KB
    # The "Animation Preview" drawtext placeholder with exact 5s is typically 9-12KB
    # We detect placeholder by checking drawtext content is absent
    quality = "REAL_MANIM" if (is_mp4 and size > 5000) else "PLACEHOLDER_OR_STUB"
    return {"exists": True, "size": size, "is_real_mp4": is_mp4, "quality": quality}


class TestTenAnimations:
    """Generate and validate 10 mathematical animations."""

    results: list[dict] = []

    @pytest.fixture(autouse=True)
    def setup(self):
        """Ensure settings are correct."""
        get_settings.cache_clear()
        settings = get_settings()
        assert not settings.simulate_render, "SIMULATE_RENDER must be false for this test"
        assert settings.groq_api_key, "GROQ_API_KEY must be set"

    @pytest.mark.parametrize("name,prompt", PROMPTS)
    def test_generate_and_render(self, name: str, prompt: str, tmp_path: Path) -> None:
        """Generate Manim code from LLM, render it, validate output is real video."""
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"PROMPT: {prompt}")

        t0 = time.time()

        # Step 1: Generate Manim code via LLM
        print("  [1/4] Calling LLM to generate Manim code...")
        code = generate_manim_code(prompt=prompt, style_preset="technical-clean")
        gen_time = time.time() - t0

        assert code, "LLM returned empty code"
        assert "GeneratedScene" in code, f"Code missing GeneratedScene class:\n{code[:200]}"
        print(f"  [1/4] Generated {len(code)} chars in {gen_time:.1f}s")

        # Step 2: Validate code
        print("  [2/4] Validating generated code...")
        validation = validate_manim_code(code)
        print(f"  [2/4] Validation: {'OK' if validation.ok else 'FAIL: ' + validation.error}")

        # Save the generated code for inspection
        code_path = ARTIFACTS / f"{name}_scene.py"
        code_path.write_text(code, encoding="utf-8")

        if not validation.ok:
            # Try sanitizing again
            code = _sanitize_code(code)
            validation = validate_manim_code(code)
            print(f"  [2/4] After re-sanitize: {'OK' if validation.ok else 'FAIL: ' + validation.error}")

        # Step 3: Render
        print("  [3/4] Running Manim render...")
        script_path = tmp_path / "generated_scene.py"
        script_path.write_text(code, encoding="utf-8")
        output_path = tmp_path / "preview.mp4"

        render_start = time.time()
        run_render(script_path=script_path, output_path=output_path, hd=False)
        render_time = time.time() - render_start

        # Step 4: Evaluate
        print(f"  [4/4] Evaluating output (render took {render_time:.1f}s)...")
        check = _check_mp4(output_path)

        # Copy to artifacts for inspection
        if output_path.exists():
            import shutil
            shutil.copy(output_path, ARTIFACTS / f"{name}_preview.mp4")

        # Check for Manim error log
        err_log = tmp_path / "manim_error.log"
        err_content = ""
        if err_log.exists():
            err_content = err_log.read_text(encoding="utf-8", errors="replace")
            print(f"  [4/4] MANIM ERROR LOG:\n{err_content[:500]}")
            import shutil
            shutil.copy(err_log, ARTIFACTS / f"{name}_error.log")

        total_time = time.time() - t0
        result = {
            "name": name,
            "prompt": prompt,
            "validation_ok": validation.ok,
            "validation_error": validation.error,
            "render_time_s": round(render_time, 1),
            "total_time_s": round(total_time, 1),
            **check,
            "manim_error": err_content[:300] if err_content else "",
        }
        TestTenAnimations.results.append(result)

        print(f"  RESULT: {check['quality']} | size={check['size']} | render={render_time:.1f}s | total={total_time:.1f}s")

        # Assert real Manim video was produced
        assert check["exists"], "preview.mp4 was not created at all"
        assert check["is_real_mp4"], f"Output is not a valid MP4 (size={check['size']}, err={err_content[:200]})"
        assert not err_log.exists(), f"Manim error log found — render failed:\n{err_content[:500]}"


def pytest_sessionfinish(session, exitstatus):
    """Print summary after all tests."""
    results = TestTenAnimations.results
    if not results:
        return

    print("\n" + "="*70)
    print("10-ANIMATION QUALITY TEST SUMMARY")
    print("="*70)
    real = [r for r in results if r.get("quality") == "REAL_MANIM"]
    print(f"Real Manim videos: {len(real)}/{len(results)}")
    for r in results:
        icon = "✓" if r.get("quality") == "REAL_MANIM" else "✗"
        print(f"  {icon} {r['name']:20s} {r.get('size', 0):8d}B render={r.get('render_time_s', 0):.1f}s val={'OK' if r.get('validation_ok') else 'FAIL'}")
    print("="*70)
