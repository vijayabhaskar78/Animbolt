import asyncio
from pathlib import Path

try:
    import edge_tts
except Exception:  # noqa: BLE001
    edge_tts = None


async def _generate_with_edge_tts(text: str, voice: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice)  # type: ignore[union-attr]
    await communicate.save(str(output_path))


def synthesize_tts(text: str, voice: str, output_path: Path) -> None:
    if edge_tts is None:
        output_path.write_bytes(text.encode("utf-8"))
        return

    try:
        asyncio.run(_generate_with_edge_tts(text=text, voice=voice, output_path=output_path))
    except RuntimeError:
        # When an event loop is already running (e.g. Jupyter). Spin up a fresh loop.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_generate_with_edge_tts(text=text, voice=voice, output_path=output_path))
        finally:
            loop.close()
    except Exception:  # noqa: BLE001
        output_path.write_bytes(text.encode("utf-8"))

