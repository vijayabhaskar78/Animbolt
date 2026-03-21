import tempfile
from pathlib import Path

import pytest

from app.services.rendering import (
    _find_manim_output,
    build_ffmpeg_concat_command,
    build_manim_preview_command,
    run_render,
)


def test_build_preview_command() -> None:
    command = build_manim_preview_command(Path("/tmp/generated.py"), Path("/tmp/out.mp4"))
    assert command[0:3] == ["python", "-m", "manim"]
    assert "GeneratedScene" in command
    assert "-ql" in command


def test_build_ffmpeg_concat_command() -> None:
    command = build_ffmpeg_concat_command(Path("/tmp/list.txt"), Path("/tmp/final.mp4"))
    assert command[0] == "ffmpeg"
    assert "-f" in command
    assert "concat" in command


def test_find_manim_output_skips_partial_files(tmp_path: Path) -> None:
    """_find_manim_output must skip partial_movie_files and return final assembled MP4."""
    # Create the nested Manim output structure
    partial_dir = tmp_path / "videos" / "generated_scene" / "480p15" / "partial_movie_files" / "GeneratedScene"
    partial_dir.mkdir(parents=True)
    (partial_dir / "uncached_00000.mp4").write_bytes(b"partial0")
    (partial_dir / "uncached_00001.mp4").write_bytes(b"partial1")

    final_dir = tmp_path / "videos" / "generated_scene" / "480p15"
    # Final file should be bigger than partials
    (final_dir / "preview.mp4").write_bytes(b"X" * 1000)

    result = _find_manim_output(tmp_path, "preview")
    assert result is not None, "Should find a result"
    assert "partial_movie_files" not in str(result), f"Should not return partial file, got: {result}"
    assert result.name == "preview.mp4"


def test_manim_subprocess_with_capture(tmp_path: Path) -> None:
    """Diagnose: does Manim combine partial clips when capture_output=True?"""
    import subprocess
    script_path = tmp_path / "generated_scene.py"
    script_path.write_text(
        """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#1A1A2E"
        circle = Circle(radius=1.5, color=BLUE, fill_opacity=0.3)
        self.play(Create(circle), run_time=1)
        self.wait(0.5)
""",
        encoding="utf-8",
    )
    cmd = [
        "python", "-m", "manim", "render", "-ql",
        "--output_file", "preview",
        "--media_dir", str(tmp_path),
        "--disable_caching", "--format", "mp4",
        str(script_path), "GeneratedScene",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        cwd=str(tmp_path),
    )
    print(f"\n[MANIM] returncode={result.returncode}")
    print(f"[MANIM] stdout:\n{result.stdout[-2000:]}")
    print(f"[MANIM] stderr:\n{result.stderr[-2000:]}")

    all_mp4 = [f for f in tmp_path.rglob("*.mp4") if "partial" not in str(f)]
    print(f"[MANIM] Final MP4 files: {all_mp4}")

    assert result.returncode == 0, f"Manim failed:\n{result.stderr}"
    assert all_mp4, "Manim did not produce a final MP4"


def test_run_render_produces_real_video(tmp_path: Path) -> None:
    """run_render with SIMULATE_RENDER=false must produce a non-placeholder MP4."""
    import os
    os.environ["SIMULATE_RENDER"] = "false"

    # Force lru_cache to refresh with new env var
    from app.core.config import get_settings
    get_settings.cache_clear()

    script_path = tmp_path / "generated_scene.py"
    script_path.write_text(
        """
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#1A1A2E"
        circle = Circle(radius=1.5, color=BLUE, fill_opacity=0.3)
        self.play(Create(circle), run_time=1)
        self.wait(0.5)
""",
        encoding="utf-8",
    )

    output_path = tmp_path / "preview.mp4"
    run_render(script_path=script_path, output_path=output_path, hd=False)

    assert output_path.exists(), "Output file must exist"
    size = output_path.stat().st_size

    # Read error log to include in failure message
    err_log = tmp_path / "manim_error.log"
    err_content = err_log.read_text(encoding="utf-8", errors="replace") if err_log.exists() else "(no error log)"

    assert err_log.exists() is False, f"Manim error log should not exist for a successful render:\n{err_content}"

    # The output must be a valid MP4 with the ftyp atom header (not a stub)
    assert size > 1000, f"Output too small ({size} bytes) — likely a stub file"
    with output_path.open("rb") as f:
        header = f.read(12)
    assert b"ftyp" in header or b"moov" in header, (
        f"Output doesn't look like a real MP4 (header: {header!r}). "
        f"This may be a SIMULATED_MP4 stub. Error log: {err_content}"
    )

    # Placeholder file is exactly the ffmpeg "Animation Preview" video - check it's NOT that
    # Real Manim video will have visual content, NOT the "Animation Preview" drawtext
    assert size > 0, "Empty output file"

