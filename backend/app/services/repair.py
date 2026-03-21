import re
from dataclasses import dataclass

from app.services.groq_adapter import generate_manim_code
from app.services.manim_validator import ValidationResult, validate_manim_code


@dataclass(slots=True)
class RepairResult:
    code: str
    validation: ValidationResult
    attempts: int


# ---------------------------------------------------------------------------
# Layout auto-correction — structural fixes applied before validation
# ---------------------------------------------------------------------------

def _fix_layout(code: str) -> str:
    """
    Apply automatic layout corrections to catch common LLM mistakes
    that cause visual misalignment without causing Python errors.

    Fixes applied:
    1. title not moved to top edge → add .to_edge(UP, buff=0.5)
    2. axes without .move_to(DOWN*0.8) when a title is present
    3. graph label placed at get_start() → change to get_end()
    4. next_to() calls missing buff → add buff=0.3
    5. Objects placed below y=-3.2 (bottom clip zone)
    """

    # Fix 1: If there's a `title = Text(...)` line but no to_edge(UP) on it,
    # add it. Look for the assignment followed by its own line.
    # Pattern: `title = Text(...)` line NOT followed by `.to_edge(UP`
    # Strategy: replace `title = Text(...)` (single-line) without trailing to_edge
    def fix_title_edge(c: str) -> str:
        lines = c.split("\n")
        result = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # Detect lines like: title = Text(...)  or  title = Text(...).something_NOT_to_edge
            stripped = line.strip()
            if (
                re.match(r'^title\s*=\s*Text\s*\(', stripped)
                and "to_edge" not in stripped
                and "move_to" not in stripped
            ):
                result.append(line)
                # Check if the NEXT non-empty line calls to_edge on title
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                next_code = lines[j].strip() if j < len(lines) else ""
                if not (next_code.startswith("title.to_edge") or next_code.startswith("title.move_to")):
                    # Infer indentation
                    indent = len(line) - len(line.lstrip())
                    result.append(" " * indent + "title.to_edge(UP, buff=0.5)")
                i += 1
                continue
            result.append(line)
            i += 1
        return "\n".join(result)

    # Fix 2: graph_label.next_to(X.get_start(), ...) → .get_end()
    # get_start() of a sine/cosine graph is at the y-axis — causes label overlap
    code = re.sub(
        r'(\.next_to\(\s*\w+\.get_start\(\)\s*,\s*)(UL|LEFT|UP)',
        r'.next_to(\g<1>RIGHT',  # wrong direction anyway if at start
        code,
    )
    # More targeted: label.next_to(graph.get_start(), ...) → get_end()
    code = re.sub(
        r'(\w+_label\s*\.next_to\s*\(\s*\w+_graph\.)(get_start\(\))',
        r'\1get_end()',
        code,
    )
    # Also fix: .next_to(sin_graph.get_start() or cos_graph.get_start()
    code = re.sub(
        r'(next_to\s*\(\s*(?:sin_graph|cos_graph|graph)\.)(get_start\(\))',
        r'\1get_end()',
        code,
    )

    # Fix 3: next_to() without buff argument → add buff=0.3
    # Match: .next_to(obj, DIRECTION) without buff= already present
    def add_buff_to_next_to(c: str) -> str:
        # Pattern: .next_to(<something>, <DIRECTION>) with no buff keyword
        # We add buff=0.3 at the end if it's missing
        return re.sub(
            r'(\.next_to\s*\(\s*[^)]+,\s*(?:UP|DOWN|LEFT|RIGHT|UL|UR|DL|DR|[A-Z_]+)\s*\))',
            lambda m: m.group(0) if 'buff' in m.group(0) else m.group(0)[:-1] + ', buff=0.3)',
            c,
        )

    code = add_buff_to_next_to(code)

    # Fix 4: Clipping at bottom — objects placed at DOWN*3.5 or more
    # Replace unsafe y positions: DOWN * N where N >= 3.3 → DOWN * 3.0
    def fix_bottom_clip(c: str) -> str:
        def clamp_down(m):
            val = float(m.group(1))
            if val >= 3.3:
                return f"DOWN * 3.0"
            return m.group(0)
        return re.sub(r'DOWN\s*\*\s*(\d+\.?\d*)', clamp_down, c)

    code = fix_bottom_clip(code)

    # Fix 5: Explicit y coordinates below -3.2 in np.array
    def fix_np_y(c: str) -> str:
        def clamp_np(m):
            y_str = m.group(2)
            try:
                y = float(y_str)
                if y < -3.2:
                    return f"np.array([{m.group(1)}, -3.0, 0])"
            except ValueError:
                pass
            return m.group(0)
        return re.sub(r'np\.array\(\[([^,]+),\s*(-\d+\.?\d*)\s*,\s*0\]\)', clamp_np, c)

    code = fix_np_y(code)

    # Apply Fix 1 last (needs line-by-line processing)
    code = fix_title_edge(code)

    return code


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_with_repair(
    prompt: str,
    style_preset: str,
    max_attempts: int = 3,
    llm_provider: str | None = None,
    max_duration_sec: int = 30,
) -> RepairResult:
    last_error = ""
    code = ""
    validation = ValidationResult(ok=False, error="no attempts made")
    for attempt in range(1, max_attempts + 1):
        repair_ctx = f"Previous validation error: {last_error}" if last_error else ""
        code = generate_manim_code(prompt, style_preset, repair_context=repair_ctx, llm_provider=llm_provider, max_duration_sec=max_duration_sec)
        # Apply structural layout fixes before validation
        code = _fix_layout(code)
        validation = validate_manim_code(code)
        if validation.ok:
            return RepairResult(code=code, validation=validation, attempts=attempt)
        last_error = validation.error

    return RepairResult(code=code, validation=validation, attempts=max_attempts)
