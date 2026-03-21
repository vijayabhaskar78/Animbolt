from app.services import repair


def test_generate_with_repair_succeeds_after_retry(monkeypatch) -> None:
    responses = [
        "import os\nprint('unsafe')",
        """
from manimlib import *
class GeneratedScene(Scene):
    def construct(self):
        self.wait(1)
""",
    ]

    def fake_generate(prompt: str, style_preset: str, repair_context: str = "", llm_provider: str | None = None) -> str:
        return responses.pop(0)

    monkeypatch.setattr(repair, "generate_manim_code", fake_generate)

    result = repair.generate_with_repair(prompt="test", style_preset="default", max_attempts=3)
    assert result.validation.ok is True
    assert result.attempts == 2

