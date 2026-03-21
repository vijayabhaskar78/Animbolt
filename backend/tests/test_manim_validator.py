from app.services.manim_validator import validate_manim_code


def test_validator_accepts_safe_code() -> None:
    code = """
from manimlib import *

class GeneratedScene(Scene):
    def construct(self):
        self.add(Text("hello"))
"""
    result = validate_manim_code(code)
    assert result.ok is True


def test_validator_blocks_unsafe_import() -> None:
    code = """
import os
from manimlib import *
class GeneratedScene(Scene):
    def construct(self):
        self.wait(1)
"""
    result = validate_manim_code(code)
    assert result.ok is False
    assert "import blocked" in result.error

