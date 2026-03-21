import logging
import re
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.services.presets import get_preset

logger = logging.getLogger(__name__)

# Ordered fallback chain — tried in sequence on timeout/rate-limit/error.
# ALL IDs verified working on this Groq account (probed 2026-03-21).
_GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",                  # Llama 3.3 70B — best quality
    "moonshotai/kimi-k2-instruct",               # Kimi K2 — very capable
    "compound-beta",                             # GPT OSS 120B — high quality
    "meta-llama/llama-4-scout-17b-16e-instruct", # Llama 4 Scout
    "qwen/qwen3-32b",                            # Qwen 3 32B
    "compound-beta-mini",                        # GPT OSS 20B — fast
    "llama-3.1-8b-instant",                      # fastest, last resort
]

# ---------------------------------------------------------------------------
# System prompt — loaded from skills.md for easy tuning without code changes
# ---------------------------------------------------------------------------
_SKILLS_PATH = Path(__file__).parent / "skills.md"
SYSTEM_PROMPT = _SKILLS_PATH.read_text(encoding="utf-8") if _SKILLS_PATH.exists() else ""

# ---------------------------------------------------------------------------
# Few-shot examples — small models learn best from concrete, working code.
# Three diverse examples covering: math/circles, geometry/proofs, transforms.
# ---------------------------------------------------------------------------

_EXAMPLE_1_PROMPT = "Create an animation showing the area of a circle equals pi*r²"
_EXAMPLE_1_CODE = '''```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0D0D0D"

        title = Text("Area of a Circle", font_size=44, color=WHITE, weight=BOLD)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=0.8)
        self.wait(0.5)

        # Define circle target position as a variable
        CIRCLE_POS = LEFT * 2.8 + DOWN * 0.2
        RADIUS = 1.6

        # Circle positioned directly at target
        circle = Circle(radius=RADIUS, color=BLUE, fill_opacity=0.25, stroke_width=3)
        circle.move_to(CIRCLE_POS)

        # Radius line: use explicit coordinates based on CIRCLE_POS
        r_start = CIRCLE_POS
        r_end = CIRCLE_POS + RIGHT * RADIUS
        r_line = Line(r_start, r_end, color=YELLOW, stroke_width=3)
        r_label = Text("r", font_size=32, color=YELLOW, weight=BOLD)
        r_label.move_to(r_start + RIGHT * RADIUS / 2 + DOWN * 0.38)

        self.play(Create(circle), run_time=1)
        self.play(Create(r_line), Write(r_label), run_time=0.8)
        self.wait(0.5)

        # Pie sectors — Sector() arc center is at ORIGIN when created.
        # Use shift(CIRCLE_POS) to translate, NOT move_to() which moves bounding-box center.
        n_sectors = 12
        wedges = VGroup()
        for i in range(n_sectors):
            angle_start = i * TAU / n_sectors
            sector = Sector(
                radius=RADIUS,
                angle=TAU / n_sectors,
                start_angle=angle_start,
                color=BLUE_D if i % 2 == 0 else GREEN_C,
                fill_opacity=0.5,
                stroke_width=0.5,
                stroke_color=WHITE,
            )
            sector.shift(CIRCLE_POS)  # shift(), NOT move_to() for arc mobjects
            wedges.add(sector)

        self.play(FadeOut(circle), FadeOut(r_line), FadeOut(r_label), run_time=0.4)
        self.play(FadeIn(wedges), run_time=0.8)
        self.wait(0.3)

        # Equation on right with highlight box
        eq = Text("A = πr²", font_size=60, color=YELLOW, weight=BOLD)
        eq.move_to(RIGHT * 2.8 + DOWN * 0.2)
        box = SurroundingRectangle(eq, color=GOLD, buff=0.25, corner_radius=0.12, stroke_width=2.5)

        self.play(Write(eq), run_time=1.2)
        self.play(Create(box), run_time=0.5)
        self.play(Indicate(eq, color=WHITE, scale_factor=1.08), run_time=0.8)
        self.wait(1.5)
```'''

_EXAMPLE_2_PROMPT = (
    "Create an animation of the Pythagorean theorem with a right triangle, "
    "squares on each side, and the equation a²+b²=c²"
)
_EXAMPLE_2_CODE = '''```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0D0D0D"

        title = Text("Pythagorean Theorem", font_size=44, color=WHITE, weight=BOLD)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=0.8)
        self.wait(0.5)

        # Right triangle (3-4-5 scaled to fit screen)
        s = 0.55
        A = np.array([0, 0, 0])
        B = np.array([3 * s, 0, 0])
        C = np.array([0, 4 * s, 0])

        triangle = Polygon(A, B, C, color=WHITE, fill_opacity=0.15, stroke_width=3)
        angle_mark = Square(side_length=0.22, color=WHITE, stroke_width=2)
        angle_mark.move_to(A + np.array([0.11, 0.11, 0]))

        # Squares on each side using perpendicular construction
        def make_sq(p1, p2, col, flip=False):
            vec = p2 - p1
            perp = np.array([-vec[1], vec[0], 0])
            if flip:
                perp = -perp
            return Polygon(p1, p2, p2 + perp, p1 + perp,
                           color=col, fill_opacity=0.3, stroke_width=2)

        sq_a = make_sq(A, B, YELLOW, flip=True)    # square below base (side a)
        sq_b = make_sq(A, C, GREEN)                 # square left of height (side b)
        sq_c = make_sq(B, C, RED, flip=True)        # square on hypotenuse (side c)

        # Group ALL geometry and center on left half of screen BEFORE labels
        geo = VGroup(triangle, angle_mark, sq_a, sq_b, sq_c)
        geo.move_to(LEFT * 2.5 + DOWN * 0.3)

        # Labels at side midpoints — positioned AFTER geo is centered
        # Use next_to() on the squares themselves for clarity, not raw midpoints
        v = triangle.get_vertices()
        la = Text("a", font_size=28, color=YELLOW, weight=BOLD)
        lb = Text("b", font_size=28, color=GREEN, weight=BOLD)
        lc = Text("c", font_size=28, color=RED, weight=BOLD)
        la.next_to(sq_a, DOWN, buff=0.15)          # below the bottom square
        lb.next_to(sq_b, LEFT, buff=0.15)           # left of the left square
        lc.next_to(sq_c, UR, buff=0.15)             # upper-right of hypotenuse square

        # Animate step by step
        self.play(Create(triangle), Create(angle_mark), run_time=1)
        self.play(Write(la), Write(lb), Write(lc), run_time=0.8)
        self.wait(0.5)

        self.play(LaggedStart(
            Create(sq_a), Create(sq_b), Create(sq_c),
            lag_ratio=0.3,
        ), run_time=2)
        self.wait(0.3)

        # Area labels centered inside each square
        la2 = Text("a²", font_size=24, color=YELLOW, weight=BOLD)
        lb2 = Text("b²", font_size=24, color=GREEN, weight=BOLD)
        lc2 = Text("c²", font_size=24, color=RED, weight=BOLD)
        la2.move_to(sq_a.get_center())
        lb2.move_to(sq_b.get_center())
        lc2.move_to(sq_c.get_center())
        self.play(Write(la2), Write(lb2), Write(lc2), run_time=0.8)
        self.wait(0.3)

        # Equation on right side with highlight box
        eq = Text("a² + b² = c²", font_size=52, color=YELLOW, weight=BOLD)
        eq.move_to(RIGHT * 3.0 + DOWN * 0.3)
        box = SurroundingRectangle(eq, color=GOLD, buff=0.22, corner_radius=0.1, stroke_width=2.5)

        self.play(Write(eq), run_time=1)
        self.play(Create(box), run_time=0.5)
        self.play(Indicate(eq, color=WHITE, scale_factor=1.06), run_time=0.8)
        self.wait(1)
```'''

_EXAMPLE_3_PROMPT = "Animate sine wave properties: amplitude, period, and the unit circle"
_EXAMPLE_3_CODE = '''```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0D0D0D"

        title = Text("Sine Wave Properties", font_size=44, color=WHITE, weight=BOLD)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=0.8)
        self.wait(0.5)

        # Axes for the sine graph — placed in lower center
        axes = Axes(
            x_range=[0, 2 * PI, PI / 2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=9,
            y_length=3.5,
            tips=True,
            axis_config={"color": WHITE, "stroke_width": 2},
        )
        axes.move_to(DOWN * 0.8)

        # Use get_axis_labels to avoid overlapping the axes
        axis_labels = axes.get_axis_labels(
            x_label=Text("x", font_size=26, color=WHITE),
            y_label=Text("y", font_size=26, color=WHITE),
        )

        self.play(Create(axes), Write(axis_labels), run_time=1)
        self.wait(0.3)

        # Plot sine wave
        sin_graph = axes.plot(
            lambda x: np.sin(x),
            x_range=[0, 2 * PI],
            color=BLUE_D,
            stroke_width=3,
        )
        # Label at END of curve — avoids y-axis overlap
        sin_label = Text("sin(x)", font_size=28, color=BLUE_D, weight=BOLD)
        sin_label.next_to(sin_graph.get_end(), RIGHT, buff=0.3)

        self.play(Create(sin_graph), run_time=1.5)
        self.play(Write(sin_label), run_time=0.5)
        self.wait(0.5)

        # Highlight amplitude with a vertical line and label
        peak_x = PI / 2
        peak_point = axes.c2p(peak_x, 1)
        base_point = axes.c2p(peak_x, 0)
        amp_line = Line(base_point, peak_point, color=YELLOW, stroke_width=3)
        amp_label = Text("A = 1", font_size=26, color=YELLOW, weight=BOLD)
        amp_label.next_to(amp_line, RIGHT, buff=0.2)

        self.play(Create(amp_line), Write(amp_label), run_time=0.8)
        self.wait(0.5)

        # Show period marker
        period_line = DashedLine(
            axes.c2p(0, -1.3),
            axes.c2p(2 * PI, -1.3),
            color=GREEN_C, stroke_width=2, dash_length=0.15,
        )
        period_label = Text("Period = 2π", font_size=26, color=GREEN_C, weight=BOLD)
        period_label.next_to(period_line, DOWN, buff=0.2)

        self.play(Create(period_line), Write(period_label), run_time=0.8)
        self.wait(1)
```'''

# ---------------------------------------------------------------------------
# Code extraction & sanitization
# ---------------------------------------------------------------------------


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _sanitize_code(code: str) -> str:
    """Fix common LLM hallucinations that cause Manim runtime errors."""
    # 0. Strip thinking blocks from various models (Qwen, Mistral, etc.)
    code = re.sub(r"<think>.*?</think>", "", code, flags=re.DOTALL)
    code = re.sub(r"<\|.*?\|>", "", code)
    code = re.sub(r"</?s>", "", code)
    code = code.lstrip("\n")

    # 1. camera.frame.animate only works on MovingCameraScene.
    # Strip it only when the class uses plain Scene — if MovingCameraScene is present, keep it.
    if "MovingCameraScene" not in code:
        code = re.sub(
            r"self\.play\(self\.camera\.frame\.animate[^)]*(?:\.[^)]*)*\)[^\n]*",
            "self.wait(0.5)  # camera zoom removed (requires MovingCameraScene)",
            code,
        )
        code = re.sub(
            r"self\.camera\.frame\.animate[^\n,)]*(?:\.[^\n,)]*)*",
            "",
            code,
        )

    # 2. MathTex / Tex → Text
    code = re.sub(r"\bMathTex\b", "Text", code)
    code = re.sub(r"\bTex\b(?!\w)", "Text", code)

    # 3. get_corner(int) → get_vertices()[int]
    code = re.sub(r"\.get_corner\((\d+)\)", r".get_vertices()[\1]", code)

    # 4. ShowCreation → Create (renamed in community manim)
    code = re.sub(r"\bShowCreation\b", "Create", code)

    # 5. Force class name to GeneratedScene — renderer requires this exact name.
    # Preserve MovingCameraScene inheritance if the LLM used it for camera movement.
    code = re.sub(
        r"class\s+\w+\(\s*\w*Scene\w*\s*\)",
        lambda m: "class GeneratedScene(MovingCameraScene)" if "MovingCamera" in m.group() else "class GeneratedScene(Scene)",
        code,
    )

    # 6. Ensure background color is set
    if "background_color" not in code:
        code = code.replace(
            "def construct(self):",
            'def construct(self):\n        self.camera.background_color = "#0D0D0D"',
            1,
        )

    # 7. Remove print statements (no use in headless rendering)
    code = re.sub(r"^\s*print\(.*\)\s*$", "", code, flags=re.MULTILINE)

    # 8. FadeInFromDown/FadeInFrom → FadeIn (deprecated)
    code = re.sub(r"\bFadeInFromDown\b", "FadeIn", code)
    code = re.sub(r"\bFadeInFrom\b(?!\w)", "FadeIn", code)

    # 9. GrowFromCenter → FadeIn (sometimes hallucinated for wrong mobject types)
    # Actually GrowFromCenter is valid in community manim, so leave it.

    # 10. Line(..., dashed=True) → DashedLine(...) — dashed is not a Line kwarg
    # Pattern: Line( ... dashed=True ... ) → DashedLine( ... ) (strip dashed kwarg)
    code = re.sub(r"\bLine\b", "_LINE_PLACEHOLDER_", code)
    code = re.sub(
        r"_LINE_PLACEHOLDER_\(([^)]*?),\s*dashed\s*=\s*True([^)]*?)\)",
        r"DashedLine(\1\2)",
        code,
    )
    code = re.sub(r"_LINE_PLACEHOLDER_", "Line", code)

    # 11. Arrow(..., dashed=True) / other Mobjects with invalid dashed kwarg
    code = re.sub(r",\s*dashed\s*=\s*True", "", code)
    code = re.sub(r",\s*dashed\s*=\s*False", "", code)

    # 12. get_corner(direction) with direction constants (e.g. get_corner(DL)) — valid,
    # but get_corner(0) / get_corner(1) is not — already handled in rule 3.

    # 13. NumberPlane.get_graph() → NumberPlane.plot() (API rename in v0.18+)
    code = re.sub(r"\.get_graph\(", ".plot(", code)

    # 14. self.setup_axes() called on Scene (only valid on GraphScene which is removed)
    code = re.sub(r"\bself\.setup_axes\(\)", "pass  # setup_axes removed", code)

    # 15. GraphScene → Scene (GraphScene removed in v0.15+; use Axes instead)
    code = re.sub(r"\bGraphScene\b", "Scene", code)

    # 16. ParametricFunction → always_redraw or ParametricFunction with correct args
    # LLMs sometimes omit t_range: add safe default if missing
    # (This is hard to fix automatically; leave it to the LLM instructions)

    # 17. ValueTracker.get_value called as attribute, not method
    # (Also too complex to regex-fix safely)

    # 18. AnnularSector/Sector with move_to() → should use shift() instead.
    # LLMs often write sector.move_to(pos) which moves bounding box center, not arc center.
    # Detect the pattern: variable.move_to(pos) where variable was assigned as Sector/AnnularSector
    # Strategy: find Sector variable names and replace their .move_to( with .shift(
    sector_vars = set(re.findall(r'(\w+)\s*=\s*(?:Sector|AnnularSector)\s*\(', code))
    for var in sector_vars:
        # Replace var.move_to( with var.shift( to fix arc-center positioning
        code = re.sub(
            r'\b' + re.escape(var) + r'\.move_to\(',
            var + '.shift(',
            code,
        )

    # 19. Replace Unicode math characters with ASCII equivalents — applied globally.
    # LLMs sometimes produce ², ³, π, α, β, θ etc. which become \ufffd replacement chars
    # in Manim's font rendering pipeline, causing Write() / Transform() to fail silently.
    # Apply globally (not just inside Text()) because unicode can appear in f-strings,
    # variable values, comments-turned-strings, etc.
    _UNICODE_MATH_MAP = [
        ("\u00b2", "^2"),    # ²
        ("\u00b3", "^3"),    # ³
        ("\u00b9", "^1"),    # ¹
        ("\u2070", "^0"),    # ⁰
        ("\u2074", "^4"),    # ⁴
        ("\u2075", "^5"),    # ⁵
        ("\u2076", "^6"),    # ⁶
        ("\u2077", "^7"),    # ⁷
        ("\u2078", "^8"),    # ⁸
        ("\u2079", "^9"),    # ⁹
        ("\u2080", "_0"),    # ₀
        ("\u2081", "_1"),    # ₁
        ("\u2082", "_2"),    # ₂
        ("\u2083", "_3"),    # ₃
        ("\u03c0", "pi"),    # π
        ("\u03b1", "alpha"), # α
        ("\u03b2", "beta"),  # β
        ("\u03b8", "theta"), # θ
        ("\u03bb", "lambda"),# λ
        ("\u03bc", "mu"),    # μ
        ("\u03c3", "sigma"), # σ
        ("\u221e", "inf"),   # ∞
        ("\u221a", "sqrt"),  # √
        ("\u2248", "~"),     # ≈
        ("\u2260", "!="),    # ≠
        ("\u2264", "<="),    # ≤
        ("\u2265", ">="),    # ≥
        ("\u00d7", "x"),     # ×
        ("\u00f7", "/"),     # ÷
        ("\u00b1", "+/-"),   # ±
        ("\u2212", "-"),     # − (minus sign, not hyphen)
        ("\u2014", " - "),   # — (em dash)
        ("\u2013", " - "),   # – (en dash)
        ("\u00b0", " deg"),  # °
        ("\u2192", "->"),    # →
        ("\u2190", "<-"),    # ←
        ("\u2194", "<->"),   # ↔
        ("\u22c5", "*"),     # ⋅ (dot product)
        ("\u00b7", "*"),     # · (middle dot)
    ]
    for uni_char, ascii_rep in _UNICODE_MATH_MAP:
        code = code.replace(uni_char, ascii_rep)

    # 20. Conclusion text overlap fix — LLMs place "Sorted!" / "Complete" text at
    # move_to(ORIGIN) or move_to(DOWN * 0.5) which puts it on top of bars/shapes.
    # Replace any such placement on conclusion-like text variables with to_edge(DOWN).
    _CONCLUSION_WORDS = r"(?:done|sorted|complete|finish|result|conclusion|final|end|success)"
    # Match: <var>.move_to(ORIGIN) or <var>.move_to(DOWN * <small_num>)
    # where var name contains a conclusion word
    code = re.sub(
        r'(\b' + _CONCLUSION_WORDS + r'\w*)\s*\.move_to\(\s*(?:ORIGIN|DOWN\s*\*\s*[01](?:\.\d+)?|UP\s*\*\s*0\.\d+)\s*\)',
        r'\1.to_edge(DOWN, buff=0.8)',
        code,
        flags=re.IGNORECASE,
    )

    return code


# ---------------------------------------------------------------------------
# Fallback scene when LLM call fails entirely
# ---------------------------------------------------------------------------


def _fallback_code(prompt: str) -> str:
    """High-quality fallback code when LLM is unavailable.
    Targets ~30 seconds: 12 play calls * 1.0s avg + 12 wait calls * 1.5s avg = ~30s.
    Uses #0D0D0D background unless prompt explicitly requests another color.
    """
    safe_prompt = prompt.replace('"', "'").strip()[:60]
    return f'''
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        self.camera.background_color = "#0D0D0D"

        # ── Title ──────────────────────────────────────────────────────
        title = Text("{safe_prompt}", font_size=40, color=WHITE, weight=BOLD)
        title.to_edge(UP, buff=0.5)
        self.play(Write(title), run_time=1.0)
        self.wait(1.0)

        # ── Introduction label ─────────────────────────────────────────
        intro = Text("Let\\'s explore this step by step", font_size=28, color=YELLOW)
        intro.move_to(UP * 1.5)
        self.play(FadeIn(intro), run_time=0.8)
        self.wait(1.2)

        # ── Step 1: Core concept shape ─────────────────────────────────
        shape = Circle(radius=1.6, color=BLUE, fill_opacity=0.25, stroke_width=3)
        shape.move_to(LEFT * 2.5 + DOWN * 0.3)
        self.play(Create(shape), run_time=1.2)
        self.wait(1.0)

        # ── Step 2: Radius line ────────────────────────────────────────
        r_line = Line(shape.get_center(), shape.get_center() + RIGHT * 1.6, color=YELLOW, stroke_width=3)
        r_label = Text("r", font_size=30, color=YELLOW, weight=BOLD)
        r_label.next_to(r_line, DOWN, buff=0.2)
        self.play(Create(r_line), Write(r_label), run_time=1.0)
        self.wait(1.2)

        # ── Step 3: Fade intro, show equation ─────────────────────────
        self.play(FadeOut(intro), run_time=0.5)
        self.wait(0.5)

        eq = Text("A = \u03c0r\u00b2", font_size=56, color=YELLOW, weight=BOLD)
        eq.move_to(RIGHT * 2.8 + DOWN * 0.2)
        self.play(Write(eq), run_time=1.5)
        self.wait(1.5)

        # ── Step 4: Highlight box ──────────────────────────────────────
        box = SurroundingRectangle(eq, color=GOLD, buff=0.25, stroke_width=2.5)
        self.play(Create(box), run_time=0.8)
        self.wait(1.0)

        # ── Step 5: Emphasize ──────────────────────────────────────────
        self.play(Indicate(eq, color=WHITE, scale_factor=1.1), run_time=1.0)
        self.wait(1.5)

        # ── Step 6: Conclusion label ───────────────────────────────────
        self.play(FadeOut(shape, r_line, r_label), run_time=0.8)
        self.wait(0.5)

        conclusion = Text("This is the key relationship.", font_size=30, color=WHITE)
        conclusion.next_to(eq, DOWN, buff=0.6)
        self.play(Write(conclusion), run_time=1.0)
        self.wait(2.0)

        # ── Final fade ─────────────────────────────────────────────────
        self.play(FadeOut(title, eq, box, conclusion), run_time=1.0)
        self.wait(0.5)
'''


# ---------------------------------------------------------------------------
# Message construction with few-shot examples
# ---------------------------------------------------------------------------


def _build_messages(user_prompt: str) -> list[dict]:
    """Build message list for code generation.

    NOTE: We intentionally do NOT include few-shot examples as assistant messages.
    When examples are in the message chain, smaller models copy them wholesale for
    any topic they don't recognise (e.g. asking for bubble sort → model outputs the
    circle-area example with the title changed). The system prompt (skills.md) already
    contains enough structure guidance.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


# ---------------------------------------------------------------------------
# LLM provider calls
# ---------------------------------------------------------------------------


def _call_groq_model(model: str, messages: list[dict], settings) -> str:  # type: ignore[no-untyped-def]
    """Call Groq for a specific model. Raises on failure."""
    payload = {"model": model, "messages": messages, "temperature": 0.4}
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
    with httpx.Client(timeout=45) as client:
        response = client.post(
            f"{settings.groq_base_url}/chat/completions",
            headers=headers, json=payload,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def _call_groq(messages: list[dict], settings) -> str:  # type: ignore[no-untyped-def]
    """Call Groq with automatic model fallback on timeout or error."""
    # Build ordered list: configured model first, then fallbacks (deduped)
    primary = settings.groq_model or _GROQ_FALLBACK_MODELS[0]
    chain = [primary] + [m for m in _GROQ_FALLBACK_MODELS if m != primary]

    last_err: Exception = RuntimeError("No models in fallback chain")
    for model in chain:
        try:
            logger.info("Groq: trying model %s", model)
            result = _call_groq_model(model, messages, settings)
            if model != primary:
                logger.info("Groq: succeeded with fallback model %s", model)
            return result
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
            logger.warning("Groq: model %s timed out, trying next", model)
            last_err = exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # 401/403 = bad API key — no point trying other models
            if status in (401, 403):
                logger.error("Groq: auth error %s — check GROQ_API_KEY", status)
                raise
            # 404 = model not found on this account, 429 = rate limit, 503/504 = overloaded
            logger.warning("Groq: model %s returned %s, trying next", model, status)
            last_err = exc
        except Exception as exc:
            logger.warning("Groq: model %s failed (%s), trying next", model, exc)
            last_err = exc

    raise last_err


def _call_ollama(messages: list[dict], settings) -> str:  # type: ignore[no-untyped-def]
    """Call local Ollama instance (OpenAI-compatible /v1/chat/completions)."""
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "temperature": 0.1,
        "stream": False,
    }
    with httpx.Client(timeout=300) as client:  # local models can be slow
        response = client.post(
            f"{settings.ollama_base_url}/v1/chat/completions",
            json=payload,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Code quality validation
# ---------------------------------------------------------------------------


def _is_acceptable_quality(code: str, prompt: str = "", min_duration_sec: int = 13) -> bool:
    """Validate generated code meets minimum quality and topic-accuracy thresholds."""
    wait_count = code.count("self.wait(")
    line_count = len([ln for ln in code.split("\n") if ln.strip() and not ln.strip().startswith("#")])

    if wait_count < 6:
        logger.debug(f"Quality FAIL: only {wait_count} waits (need 6+)")
        return False

    if line_count < 30:
        logger.debug(f"Quality FAIL: only {line_count} lines (need 30+)")
        return False

    if "self.play(" not in code:
        logger.debug("Quality FAIL: no self.play() calls")
        return False

    # Duration estimate — must reach at least 60% of the requested duration
    wait_vals = re.findall(r'self\.wait\((\d+\.?\d*)\)', code)
    total_wait = sum(float(v) for v in wait_vals) if wait_vals else float(wait_count)
    play_count = code.count('self.play(')
    estimated_duration = total_wait + play_count * 0.8
    if estimated_duration < min_duration_sec:
        logger.debug(f"Quality FAIL: estimated duration {estimated_duration:.1f}s (need {min_duration_sec}s+)")
        return False

    # Topic relevance: key words from the prompt must appear in the generated code.
    # This catches the critical failure where the model outputs a generic template
    # (e.g., circle + "A=πr²") for a completely different topic (e.g., bubble sort).
    if prompt:
        _STOP = {
            "a","an","the","and","or","of","in","on","to","for","with","that",
            "this","is","are","was","be","by","as","at","it","its","from","how",
            "show","animate","create","make","step","each","into","using","use",
            "give","me","us","let","can","will","also","all","some","any","build",
            "building","understanding","visualize","explain","display","demonstrate",
            "draw","plot","render","generate","educational","mathematical",
        }
        prompt_words = [w for w in re.findall(r'[a-zA-Z]{4,}', prompt.lower()) if w not in _STOP]
        code_lower = code.lower()
        if prompt_words and not any(w in code_lower for w in prompt_words):
            logger.debug(
                f"Quality FAIL: prompt keywords {prompt_words[:6]} absent from code — "
                "model output is off-topic (likely copied a template)."
            )
            return False

    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def generate_manim_code(
    prompt: str,
    style_preset: str,
    repair_context: str = "",
    llm_provider: str | None = None,
    max_attempts: int = 2,
    max_duration_sec: int = 30,
) -> str:
    settings = get_settings()
    provider = llm_provider or settings.llm_provider  # request override > env default

    preset = get_preset(style_preset)
    style_instruction = preset.system_hint if preset else f"Style: {style_preset}"

    # Detect if user wants a specific background color
    prompt_lower = prompt.lower()
    color_keywords = [
        "black background", "white background", "dark background", "light background",
        "red background", "green background", "yellow background", "purple background",
        "blue background", "navy background", "orange background", "pink background",
        "grey background", "gray background", "teal background", "cyan background",
        "background color", "background should be", "background is",
        "navy blue", "dark blue", "bright background", "colorful background",
    ]
    user_wants_custom_color = any(kw in prompt_lower for kw in color_keywords)

    bg_instruction = (
        "Background color: respect the user's color request. If no color mentioned, use #0D0D0D (near-black)."
        if user_wants_custom_color
        else "Background: self.camera.background_color = \"#0D0D0D\"  (near-black, NOT blue)"
    )

    # Detect topic type to give the LLM a targeted hint
    pl = prompt.lower()
    if any(w in pl for w in ["sort", "search", "algorithm", "graph traversal", "bfs", "dfs", "dijkstra", "tree", "linked list", "stack", "queue", "hash"]):
        topic_hint = (
            "TOPIC TYPE: Computer Science / Algorithm\n"
            "  → Use Rectangle() bars or Dot()/Line() nodes to visualise the data structure\n"
            "  → Animate actual operations: swaps=move bars, comparisons=highlight RED, done=GREEN\n"
            "  → Show each step of the algorithm explicitly with labels\n"
        )
    elif any(w in pl for w in ["calculus", "derivative", "integral", "limit", "differential", "taylor", "fourier"]):
        topic_hint = (
            "TOPIC TYPE: Calculus\n"
            "  → Use Axes() + ax.plot() for curves\n"
            "  → Animate tangent lines, shaded areas, limit approaches\n"
            "  → Label axes, key points, and the main equation\n"
        )
    elif any(w in pl for w in ["geometry", "triangle", "circle", "polygon", "proof", "theorem", "angle", "vector", "matrix"]):
        topic_hint = (
            "TOPIC TYPE: Mathematics / Geometry\n"
            "  → Draw the actual geometric figures with correct proportions\n"
            "  → Label every side, angle, and key measurement\n"
            "  → Animate the proof or construction step by step\n"
        )
    elif any(w in pl for w in ["physics", "force", "motion", "wave", "energy", "newton", "gravity", "velocity", "acceleration"]):
        topic_hint = (
            "TOPIC TYPE: Physics\n"
            "  → Use Arrow() for force/velocity vectors with magnitude labels\n"
            "  → Show moving objects, annotate with Text() values\n"
            "  → Animate the physical process over time\n"
        )
    elif any(w in pl for w in ["rocket", "launch", "space", "moon", "planet", "orbit", "asteroid", "galaxy", "satellite", "atmosphere", "earth", "solar", "star", "comet", "spacecraft", "journey", "travel through", "zoom out", "zoom in", "fly through"]):
        topic_hint = (
            "TOPIC TYPE: Spatial Journey / Camera Movement\n"
            "  → Use MovingCameraScene (NOT Scene) as the base class\n"
            "  → Use self.camera.frame.animate.scale(N) to zoom out as objects move\n"
            "  → Use self.camera.frame.animate.move_to(obj) to follow moving objects\n"
            "  → Chain both: self.camera.frame.animate.scale(2).move_to(rocket)\n"
            "  → NEVER let objects fly off screen — zoom the camera out instead\n"
            "  → Animate the full journey: start scene → travel → destination\n"
        )
    else:
        topic_hint = (
            "TOPIC TYPE: General Educational\n"
            "  → Identify the core concept and build a clear visual metaphor for it\n"
            "  → Show the concept step by step with labeled diagrams\n"
        )

    # Calculate call counts required to hit the target duration.
    # Average: each self.play() ≈ 1.2s, each self.wait() ≈ 1.2s
    # So total calls needed ≈ max_duration_sec / 1.2, split evenly.
    _total_calls = max(24, int(max_duration_sec / 1.2))
    _play_calls  = _total_calls // 2
    _wait_calls  = _total_calls - _play_calls
    _min_lines   = max(60, max_duration_sec * 2)  # more seconds → more code

    user_prompt = (
        f"GENERATE A MANIM ANIMATION FOR: {prompt}\n\n"
        f"{topic_hint}\n"
        f"DURATION: Exactly {max_duration_sec} seconds — this is mandatory.\n"
        f"  sum(run_time values) + sum(self.wait() values) MUST equal ~{max_duration_sec}s\n"
        f"  Need ~{_play_calls} self.play() calls (run_time=1.0–2.0 each)\n"
        f"  Need ~{_wait_calls} self.wait() calls (each 1.0–2.5s, NOT 0.5s)\n"
        f"  SHORT self.wait(0.5) calls will make the video too short — use self.wait(1.5) minimum\n\n"
        f"{bg_instruction}\n\n"
        "REQUIREMENTS:\n"
        "  • NO TITLE/HEADING unless the user explicitly asked for one — dive straight into the animation\n"
        "  • Build objects → position with move_to()/next_to() → THEN animate\n"
        "  • Labels: label.next_to(shape, DIRECTION, buff=0.3) — never at ORIGIN\n"
        "  • Safe zone: x ∈ [-6,6], y ∈ [-3.2,3.5]\n"
        f"  • At least {_min_lines} lines of code\n"
        "  • NO MathTex, NO Tex, NO ShowCreation, NO GraphScene (they will crash)\n"
        "  • Use Text() for all text, Create() instead of ShowCreation\n"
        "  • If objects travel large distances, use MovingCameraScene + self.camera.frame.animate.scale(N) to zoom out — never let objects fly off-screen\n\n"
        f"{'Repair context: ' + repair_context if repair_context else ''}"
        "Return ONLY the Python code inside a ```python block."
    )

    messages = _build_messages(user_prompt)

    for attempt in range(max_attempts):
        try:
            if provider == "ollama":
                content = _call_ollama(messages, settings)
            elif settings.groq_api_key:
                content = _call_groq(messages, settings)
            else:
                return _fallback_code(prompt)

            code = _sanitize_code(_extract_code(content))

            # Quality check: enforce at least 75% of requested duration
            _min_dur = max(13, int(max_duration_sec * 0.75))
            if _is_acceptable_quality(code, prompt, min_duration_sec=_min_dur):
                logger.debug(f"Code generation passed quality check on attempt {attempt + 1}")
                return code
            else:
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"Generated code failed quality check (attempt {attempt + 1}/{max_attempts}), "
                        "retrying with stricter prompt..."
                    )
                    # Retry demanding the correct duration explicitly
                    user_prompt += (
                        f"\n\nCRITICAL: Previous attempt was too SHORT. "
                        f"You MUST generate {max_duration_sec} seconds of animation. "
                        f"Add {_play_calls} self.play() calls and {_wait_calls} self.wait() calls. "
                        "Break the topic into many sub-steps — intro, each concept step, conclusion."
                    )
                    messages = _build_messages(user_prompt)
                else:
                    logger.warning(
                        f"Code failed quality checks after {max_attempts} attempts, returning anyway"
                    )
                    return code

        except Exception:  # noqa: BLE001
            if attempt < max_attempts - 1:
                logger.warning(f"Generation attempt {attempt + 1} failed, retrying...")
                continue
            return _fallback_code(prompt)

    return _fallback_code(prompt)


def refine_manim_code(
    existing_code: str,
    feedback: str,
    llm_provider: str | None = None,
) -> str:
    """Take existing Manim code and refine it based on user feedback.

    The LLM only edits what is necessary — structure, class name, and
    background color are preserved. Returns the full revised code.
    """
    settings = get_settings()
    provider = llm_provider or settings.llm_provider

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "You are a code refinement expert. The user has watched a Manim animation "
                "and provided feedback. Your job is to modify the EXISTING code to address their feedback.\n\n"
                f"USER FEEDBACK: {feedback}\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Make SUBSTANTIVE CHANGES to address the feedback (don't just return unchanged code)\n"
                "2. Keep the class name `GeneratedScene` and background color unchanged\n"
                "3. Keep the overall structure and concept intact\n"
                "4. Add MORE self.wait() calls if feedback mentions 'too fast' or 'rushed'\n"
                "5. Adjust run_time values if feedback mentions animation speed\n"
                "6. Change colors throughout if feedback mentions 'color scheme' (e.g., use BLUE/YELLOW/WHITE)\n"
                "7. Your code MUST be different from the original (not identical)\n"
                "8. Return the COMPLETE corrected Python code in a ```python block.\n\n"
                f"EXISTING CODE TO REFINE:\n```python\n{existing_code}\n```\n\n"
                "Now generate the IMPROVED version addressing the feedback above."
            ),
        },
    ]

    try:
        if provider == "ollama":
            content = _call_ollama(messages, settings)
        elif settings.groq_api_key:
            content = _call_groq(messages, settings)
        else:
            return existing_code

        refined = _sanitize_code(_extract_code(content))

        # Validate that code actually changed
        if refined.strip() == existing_code.strip():
            logger.warning(
                "Refinement returned identical code, trying again with explicit instruction..."
            )
            # Retry with even more explicit instruction
            messages[1]["content"] += (
                "\n\nIMPORTANT: Your response MUST be different from the input code. "
                "You MUST make changes. If the feedback says 'too fast', add self.wait() calls. "
                "If it says 'colors', change the colors. Do NOT return the same code."
            )
            try:
                if provider == "ollama":
                    content = _call_ollama(messages, settings)
                elif settings.groq_api_key:
                    content = _call_groq(messages, settings)
                else:
                    return existing_code
                refined = _sanitize_code(_extract_code(content))
            except Exception:
                logger.exception("Refinement retry failed")
                return existing_code

        return refined

    except Exception:  # noqa: BLE001
        logger.exception("refine_manim_code failed, returning original code")
        return existing_code
