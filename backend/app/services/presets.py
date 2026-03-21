from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StylePreset:
    id: str
    display_name: str
    description: str
    system_hint: str


PRESETS: dict[str, StylePreset] = {
    "technical-clean": StylePreset(
        id="technical-clean",
        display_name="Technical Clean",
        description="Crisp diagrams with minimal decoration. Ideal for system/network flows.",
        system_hint=(
            "Use a clean, minimal aesthetic. Prefer geometric shapes (Rectangle, Arrow, Line, Dot). "
            "Use BLUE, WHITE, and GRAY tones. Label every component with Text. "
            "Animate flows left-to-right. Keep whitespace generous."
        ),
    ),
    "minimal": StylePreset(
        id="minimal",
        display_name="Minimal",
        description="Black-and-white with sparse elements. Emphasises motion over decoration.",
        system_hint=(
            "Use only WHITE, BLACK, and GRAY. No fill colors. Thin strokes. "
            "Prioritise smooth transforms and simple motion. Fewer objects, more space."
        ),
    ),
    "colorful": StylePreset(
        id="colorful",
        display_name="Colorful",
        description="Vibrant palette with bold fills. Great for engaging explainer animations.",
        system_hint=(
            "Use a vivid palette: BLUE, RED, GREEN, YELLOW, ORANGE, PURPLE, PINK. "
            "Add fill_opacity=0.6 to all shapes. Animate with FadeIn, GrowArrow, DrawBorderThenFill. "
            "Make it lively and energetic."
        ),
    ),
    "educational": StylePreset(
        id="educational",
        display_name="Educational",
        description="Step-by-step reveals with clear labels. Designed for learning content.",
        system_hint=(
            "Reveal elements one at a time with Write or FadeIn animations. "
            "Label everything with descriptive Text. Use Indicate to highlight key concepts. "
            "Pause between steps with self.wait(0.5). Prefer a calm, structured layout."
        ),
    ),
    "data-viz": StylePreset(
        id="data-viz",
        display_name="Data Viz",
        description="Charts, axes, and numerical annotations. Best for data-driven scenes.",
        system_hint=(
            "Use Axes, NumberPlane, or BarChart where appropriate. "
            "Animate data with Create and Transform. Label axes and data points. "
            "Use BLUE for series, RED for highlights. Keep values plausible and illustrative."
        ),
    ),
    "conceptual": StylePreset(
        id="conceptual",
        display_name="Conceptual",
        description="Abstract shapes and metaphors to communicate ideas at a high level.",
        system_hint=(
            "Use abstract shapes (Circle, Triangle, VGroup) to represent concepts metaphorically. "
            "Animate transformations between states to show relationships. "
            "Use contrasting colors to differentiate ideas. Keep text minimal — let motion tell the story."
        ),
    ),
}


def get_preset(preset_id: str) -> StylePreset | None:
    return PRESETS.get(preset_id)


def list_presets() -> list[StylePreset]:
    return list(PRESETS.values())
