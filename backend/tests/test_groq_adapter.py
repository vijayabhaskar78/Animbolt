from app.services import groq_adapter
from app.services.groq_adapter import _sanitize_code


def test_extracts_python_fence() -> None:
    text = "```python\nprint('ok')\n```"
    assert groq_adapter._extract_code(text) == "print('ok')"


def test_fallback_contains_scene_class() -> None:
    code = groq_adapter._fallback_code("hello world")
    assert "class GeneratedScene(Scene)" in code
    assert "from manim import *" in code


def test_sanitize_dashed_line_converted_to_dashed_line_class() -> None:
    """Line(..., dashed=True) must become DashedLine(...)."""
    code = "x = Line(start, end, color=BLUE, stroke_width=2, dashed=True)"
    result = _sanitize_code(code)
    assert "DashedLine" in result, f"DashedLine not found in: {result}"
    assert "dashed=True" not in result, f"dashed=True still present in: {result}"


def test_sanitize_dashed_arg_stripped_from_other_mobjects() -> None:
    """dashed=True on any mobject should be stripped to avoid TypeError."""
    code = "arrow = Arrow(LEFT, RIGHT, color=RED, dashed=True)"
    result = _sanitize_code(code)
    assert "dashed=True" not in result, f"dashed=True still present: {result}"


def test_sanitize_normal_line_unchanged() -> None:
    """Plain Line() without dashed should not be altered."""
    code = "line = Line(LEFT * 3, RIGHT * 3, color=WHITE, stroke_width=2)"
    result = _sanitize_code(code)
    assert "Line(LEFT * 3, RIGHT * 3, color=WHITE, stroke_width=2)" in result


def test_sanitize_get_graph_to_plot() -> None:
    """axes.get_graph() must become axes.plot()."""
    code = "graph = axes.get_graph(lambda x: x**2, x_range=[0, 4])"
    result = _sanitize_code(code)
    assert ".plot(" in result
    assert ".get_graph(" not in result


def test_sanitize_graphscene_to_scene() -> None:
    """GraphScene must become Scene since it was removed in v0.15+."""
    code = "class GeneratedScene(GraphScene):\n    def construct(self): pass"
    result = _sanitize_code(code)
    assert "GraphScene" not in result
    assert "Scene" in result


def test_sanitize_setup_axes_removed() -> None:
    """self.setup_axes() must be removed (GraphScene method, not on Scene)."""
    code = "        self.setup_axes()\n        self.play(Write(title))"
    result = _sanitize_code(code)
    assert "setup_axes()" not in result or "pass" in result


def test_sanitize_maththex_converted() -> None:
    """MathTex must be replaced with Text."""
    code = "eq = MathTex('a^2 + b^2 = c^2')"
    result = _sanitize_code(code)
    assert "MathTex" not in result
    assert "Text" in result


def test_sanitize_showcreation_converted() -> None:
    """ShowCreation must be replaced with Create."""
    code = "self.play(ShowCreation(circle))"
    result = _sanitize_code(code)
    assert "ShowCreation" not in result
    assert "Create" in result


def test_sanitize_think_blocks_stripped() -> None:
    """<think> blocks from models like Qwen must be stripped."""
    code = "<think>Let me plan this...</think>\nfrom manim import *\nclass GeneratedScene(Scene): pass"
    result = _sanitize_code(code)
    assert "<think>" not in result
    assert "from manim import *" in result

