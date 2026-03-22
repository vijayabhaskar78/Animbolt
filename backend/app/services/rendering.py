import json
import logging
import subprocess
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/"
    "YVh5R0AAAAASUVORK5CYII="
)


def preview_frame_payload() -> str:
    return MINIMAL_PNG_BASE64


def build_manim_preview_command(script_path: Path, output_path: Path) -> list[str]:
    """Community manim render at 480p15 (low quality) for previews."""
    return [
        "python",
        "-m",
        "manim",
        "render",
        "-ql",
        "--output_file",
        output_path.stem,
        "--media_dir",
        str(output_path.parent),
        "--disable_caching",
        "--format",
        "mp4",
        str(script_path),
        "GeneratedScene",
    ]


def build_manim_hd_command(script_path: Path, output_path: Path) -> list[str]:
    """Community manim render at 720p30 (medium quality) for HD export."""
    return [
        "python",
        "-m",
        "manim",
        "render",
        "-qm",
        "--output_file",
        output_path.stem,
        "--media_dir",
        str(output_path.parent),
        "--disable_caching",
        "--format",
        "mp4",
        str(script_path),
        "GeneratedScene",
    ]


def _find_manim_output(job_dir: Path, stem: str) -> Path | None:
    """Find the final assembled MP4 that manim community edition wrote under media_dir/videos/...

    Manim writes partial clips to partial_movie_files/ and combines them into the
    final video at media_dir/videos/{script_stem}/{quality}/{output_file}.mp4.
    We must skip the partial clips and find the final assembled file.
    """
    candidates: list[Path] = []
    for mp4 in job_dir.rglob("*.mp4"):
        # Skip partial clip directories produced during rendering
        if "partial_movie_files" in mp4.parts:
            continue
        candidates.append(mp4)

    if not candidates:
        return None

    # Prefer a file whose stem matches the requested output name
    for mp4 in candidates:
        if mp4.stem == stem:
            return mp4

    # Otherwise return the largest non-partial file (final assembled video is biggest)
    return max(candidates, key=lambda p: p.stat().st_size)


def build_ffmpeg_concat_command(list_file: Path, output_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(output_path),
    ]


def _write_placeholder_video(path: Path) -> None:
    """Generate a real playable MP4 via ffmpeg (black screen with text).
    Falls back to a stub only if ffmpeg is not available."""
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=0x1a2a3a:size=854x480:rate=15:duration=5",
                "-vf", "drawtext=text='Animation Preview':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2",
                "-vcodec", "libx264",
                "-pix_fmt", "yuv420p",
                "-preset", "ultrafast",
                str(path),
            ],
            check=True,
            timeout=30,
            capture_output=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        path.write_bytes(b"SIMULATED_MP4")


def _log_manim_error(job_dir: Path, stderr: str, stdout: str, extra: str = "") -> None:
    """Write Manim error details to per-job and central error logs."""
    error_log = job_dir / "manim_error.log"
    content = f"=== Manim Error ===\n{extra}\n\n--- STDOUT ---\n{stdout}\n\n--- STDERR ---\n{stderr}\n"
    try:
        error_log.write_text(content, encoding="utf-8")
    except Exception:
        pass

    # Also append to central errors log
    central_log = job_dir.parent / "render_errors.log"
    try:
        with central_log.open("a", encoding="utf-8") as f:
            f.write(f"\n[{job_dir.name}]\n{extra}\n{stderr[:2000]}\n{'='*60}\n")
    except Exception:
        pass

    logger.error("Manim render failed in %s: %s\nSTDERR: %s", job_dir, extra, stderr[:2000])
    print(f"MANIM_ERROR [{job_dir.name}]: {extra}\nSTDERR: {stderr[:2000]}", flush=True)


def run_render(script_path: Path, output_path: Path, hd: bool = False) -> None:
    settings = get_settings()
    print(f"DEBUG run_render: simulate_render={settings.simulate_render!r}", flush=True)
    if settings.simulate_render:
        _write_placeholder_video(output_path)
        return

    # Convert to absolute paths to avoid cwd issues with Manim
    script_path = script_path.resolve()
    output_path = output_path.resolve()

    command = build_manim_hd_command(script_path, output_path) if hd else build_manim_preview_command(script_path, output_path)
    job_dir = output_path.parent
    try:
        result = subprocess.run(
            command,
            check=True,
            timeout=300,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        # Community manim writes to a nested subdirectory; find and move to expected path.
        found = _find_manim_output(job_dir, output_path.stem)
        if found and found.resolve() != output_path.resolve():
            found.rename(output_path)
        if not output_path.exists():
            _log_manim_error(
                job_dir,
                stderr=result.stderr,
                stdout=result.stdout,
                extra="Manim exited 0 but output MP4 not found",
            )
            _write_placeholder_video(output_path)
    except subprocess.CalledProcessError as exc:
        _log_manim_error(
            job_dir,
            stderr=exc.stderr or "",
            stdout=exc.stdout or "",
            extra=f"Manim exited with code {exc.returncode}",
        )
        _write_placeholder_video(output_path)
    except subprocess.TimeoutExpired as exc:
        _log_manim_error(
            job_dir,
            stderr=getattr(exc, "stderr", None) or "",
            stdout=getattr(exc, "stdout", None) or "",
            extra="Manim timed out after 300s",
        )
        _write_placeholder_video(output_path)
    except FileNotFoundError:
        _log_manim_error(
            job_dir,
            stderr="",
            stdout="",
            extra="Manim executable not found — is manim installed in this Python environment?",
        )
        _write_placeholder_video(output_path)


def concat_videos(input_paths: list[Path], output_path: Path) -> None:
    settings = get_settings()
    if settings.simulate_render or not input_paths:
        _write_placeholder_video(output_path)
        return

    list_file = output_path.parent / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{path.as_posix()}'" for path in input_paths), encoding="utf-8")
    try:
        subprocess.run(build_ffmpeg_concat_command(list_file, output_path), check=True, timeout=180)
    except (subprocess.SubprocessError, FileNotFoundError):
        _write_placeholder_video(output_path)


def merge_audio_video(video_path: Path, audio_path: Path, output_path: Path) -> None:
    settings = get_settings()
    if settings.simulate_render:
        _write_placeholder_video(output_path)
        return

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-shortest",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, timeout=180)
    except (subprocess.SubprocessError, FileNotFoundError):
        _write_placeholder_video(output_path)


def extract_frames(video_path: Path, output_dir: Path, n_frames: int = 20) -> list[Path]:
    """
    Extract up to *n_frames* evenly-spaced frames from *video_path* as PNGs.
    Returns the sorted list of created frame files (may be empty on failure).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", "fps=4,scale=640:-2",
                "-frames:v", str(n_frames),
                str(output_dir / "frame_%04d.png"),
            ],
            check=True,
            timeout=60,
            capture_output=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return sorted(output_dir.glob("frame_*.png"))


def extract_thumbnail(video_path: Path, output_path: Path) -> None:
    """Extract the first frame of a video as a PNG thumbnail via ffmpeg."""
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(output_path),
            ],
            check=True,
            timeout=30,
            capture_output=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        # Write a tiny 1×1 transparent PNG as fallback
        output_path.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def build_preview_event(job_id: str, frame_index: int, timestamp_ms: int) -> str:
    event = {
        "job_id": job_id,
        "frame_index": frame_index,
        "timestamp_ms": timestamp_ms,
        "mime_type": "image/png",
        "payload_base64": preview_frame_payload(),
    }
    return json.dumps(event)
