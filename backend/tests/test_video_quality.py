"""
End-to-end video quality testing and iteration framework.
Tests code generation, validation, rendering, and refinement quality.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Set UTF-8 encoding for Windows compatibility
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.groq_adapter import generate_manim_code, refine_manim_code
from app.services.manim_validator import validate_manim_code


# Test prompts covering different complexity levels and concepts
# Using fewer test cases for faster iteration
TEST_PROMPTS = [
    {
        "name": "circle_area",
        "prompt": "Area of a circle: show how to derive the formula πr² by dividing into sectors. Keep animation paced and clear with good pauses between concepts.",
        "style": "technical-clean",
    },
    {
        "name": "pythagorean",
        "prompt": "Pythagorean theorem: show a right triangle with squares on each side, prove a² + b² = c². Make the animation smooth with clear timing.",
        "style": "technical-clean",
    },
]

REFINEMENT_FEEDBACK = {
    "circle_area": "Make the color scheme more coherent - use only blue, yellow, and white. Add longer pauses between each concept reveal.",
    "pythagorean": "Make the animation slower with more time for viewers to read labels. Add 1-2 second pauses between major steps.",
}


def test_code_generation(prompt_data: dict, max_retries: int = 3) -> tuple[str, bool]:
    """Generate code for a prompt and return (code, is_valid)."""
    print(f"\n{'='*60}")
    print(f"Testing: {prompt_data['name']}")
    print(f"Prompt: {prompt_data['prompt'][:80]}...")
    print(f"{'='*60}")

    for attempt in range(1, max_retries + 1):
        try:
            # Use Groq API for testing (Ollama URL may not be accessible)
            code = generate_manim_code(
                prompt=prompt_data["prompt"],
                style_preset=prompt_data["style"],
                llm_provider="groq",
            )

            # Validate the generated code
            validation = validate_manim_code(code)

            if validation.ok:
                print(f"[PASS] Code generation PASSED (attempt {attempt}/{max_retries})")
                print(f"  Generated {len(code)} bytes of code")
                return code, True
            else:
                print(f"[FAIL] Code validation FAILED")
                print(f"  Error: {validation.error[:200]}")
                return code, False

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate" in error_msg.lower():
                # Rate limit error - retry with backoff
                if attempt < max_retries:
                    wait_time = 5 * attempt  # 5s, 10s, 15s backoff
                    print(f"[INFO] Rate limited (attempt {attempt}/{max_retries}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[FAIL] Rate limit exhausted after {max_retries} retries")
                    return "", False
            else:
                # Other error
                print(f"[FAIL] Code generation FAILED with exception")
                print(f"  Error: {error_msg[:200]}")
                return "", False

    return "", False


def test_refinement(original_code: str, feedback: str, test_name: str, max_retries: int = 3) -> tuple[str, bool]:
    """Refine code based on feedback and validate."""
    print(f"\n{'='*60}")
    print(f"Testing refinement for: {test_name}")
    print(f"Feedback: {feedback[:80]}...")
    print(f"{'='*60}")

    for attempt in range(1, max_retries + 1):
        try:
            refined_code = refine_manim_code(
                existing_code=original_code,
                feedback=feedback,
                llm_provider="groq",  # Use Groq API
            )

            # Validate the refined code
            validation = validate_manim_code(refined_code)

            if validation.ok:
                print(f"[PASS] Code refinement PASSED (attempt {attempt}/{max_retries})")
                print(f"  Generated {len(refined_code)} bytes of refined code")

                # Check if code was actually changed
                if refined_code != original_code:
                    print(f"  [OK] Code was modified (not identical)")
                    # Show a sample of changes
                    orig_lines = original_code.split('\n')
                    refined_lines = refined_code.split('\n')
                    changed_lines = sum(1 for o, r in zip(orig_lines, refined_lines) if o != r)
                    print(f"  [OK] {changed_lines} lines changed")
                else:
                    print(f"  [WARN] Code unchanged (may indicate refinement not applied)")

                return refined_code, True
            else:
                print(f"[FAIL] Refined code validation FAILED")
                print(f"  Error: {validation.error[:200]}")
                return refined_code, False

        except Exception as e:
            error_msg = str(e)
            if "rate" in error_msg.lower() or "timeout" in error_msg.lower():
                # Rate limit or timeout error - retry with backoff
                if attempt < max_retries:
                    wait_time = 5 * attempt
                    print(f"[INFO] Attempt {attempt} failed, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[FAIL] Refinement exhausted after {max_retries} retries")
                    return original_code, False
            else:
                print(f"[FAIL] Code refinement FAILED with exception")
                print(f"  Error: {error_msg[:200]}")
                return original_code, False

    return original_code, False


def check_code_quality(code: str, test_name: str) -> dict:
    """Analyze code for quality issues."""
    issues = []
    warnings = []

    # Check animation timing
    wait_count = code.count('self.wait(')
    if wait_count < 5:
        warnings.append(f"Low pause count ({wait_count}): animation may feel rushed")

    # Check for forbidden APIs
    forbidden = [
        ("MathTex", "Should use Text() instead"),
        ("ShowCreation", "Should use Create() instead"),
        ("camera.frame.animate", "Not available on Scene"),
        ("GraphScene", "Was removed; use Scene + Axes instead"),
    ]

    for api, reason in forbidden:
        if api in code:
            issues.append(f"Forbidden API: {api} ({reason})")

    # Check structure
    if 'class GeneratedScene' not in code:
        issues.append("Missing class GeneratedScene")

    if 'self.camera.background_color' not in code:
        issues.append("Missing background color setup")

    if 'def construct(self):' not in code:
        issues.append("Missing construct() method")

    # Check layout safety
    line_count = len([l for l in code.split('\n') if l.strip()])
    if line_count < 30:
        warnings.append("Very short animation (may be incomplete)")
    elif line_count > 150:
        warnings.append("Very long animation (may be over-complicated)")

    # Check for viewport safety
    has_positioning = (
        'move_to(' in code or 'to_edge(' in code or
        'shift(' in code or 'next_to(' in code
    )
    if not has_positioning:
        warnings.append("No clear positioning logic (check viewport safety)")

    # Check color consistency
    color_count = (
        code.count('BLUE') + code.count('YELLOW') +
        code.count('RED') + code.count('GREEN') +
        code.count('WHITE') + code.count('PINK')
    )
    if color_count > 10:
        warnings.append("High color usage (palette may be incoherent)")

    return {
        "issues": issues,
        "warnings": warnings,
        "line_count": line_count,
        "wait_count": wait_count,
    }


def report_test_result(test_name: str, gen_ok: bool, ref_ok: bool, quality: dict):
    """Print formatted test report."""
    print(f"\n{'─'*60}")
    print(f"TEST REPORT: {test_name}")
    print(f"{'─'*60}")

    print(f"Generation: {'[PASS]' if gen_ok else '[FAIL]'}")
    print(f"Refinement: {'[PASS]' if ref_ok else '[FAIL]'}")
    print(f"Lines: {quality['line_count']}")
    print(f"Waits: {quality['wait_count']}")

    if quality['issues']:
        print(f"\nIssues ({len(quality['issues'])}):")
        for issue in quality['issues']:
            print(f"  [!] {issue}")

    if quality['warnings']:
        print(f"\nWarnings ({len(quality['warnings'])}):")
        for warning in quality['warnings']:
            print(f"  [W] {warning}")

    if not quality['issues'] and not quality['warnings']:
        print(f"\n[OK] No issues or warnings detected")


def check_ollama_available():
    """Check if Ollama is available and accessible."""
    import httpx
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                return True
    except Exception:
        pass
    return False


def main():
    """Run comprehensive quality testing."""
    print("\n" + "="*60)
    print("COMPREHENSIVE VIDEO QUALITY TESTING")
    print("="*60)

    # Check if Ollama is available
    if not check_ollama_available():
        print("\n[!] WARNING: Ollama not detected at localhost:11434")
        print("[!] Testing will use Groq API (may hit rate limits)")
        print("[!] To use Ollama, start it with: ollama serve\n")

    results = []

    for prompt_data in TEST_PROMPTS:
        test_name = prompt_data["name"]

        # Test code generation
        code, gen_ok = test_code_generation(prompt_data)

        if gen_ok:
            # Test refinement
            feedback = REFINEMENT_FEEDBACK.get(test_name, "Improve the animation quality")
            refined_code, ref_ok = test_refinement(code, feedback, test_name)
        else:
            refined_code = code
            ref_ok = False

        # Analyze code quality
        quality = check_code_quality(code, test_name)

        # Report results
        report_test_result(test_name, gen_ok, ref_ok, quality)

        results.append({
            "name": test_name,
            "gen_ok": gen_ok,
            "ref_ok": ref_ok,
            "quality": quality,
        })

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total = len(results)
    gen_pass = sum(1 for r in results if r["gen_ok"])
    ref_pass = sum(1 for r in results if r["ref_ok"])

    print(f"Tests: {total}")
    print(f"Generation: {gen_pass}/{total} passed")
    print(f"Refinement: {ref_pass}/{total} passed")

    total_issues = sum(len(r["quality"]["issues"]) for r in results)
    total_warnings = sum(len(r["quality"]["warnings"]) for r in results)

    print(f"Total issues: {total_issues}")
    print(f"Total warnings: {total_warnings}")

    if total_issues == 0 and total_warnings == 0:
        print("\n[OK] ALL TESTS PASSED WITH NO ISSUES")
        return 0
    else:
        print(f"\n[W] Found {total_issues + total_warnings} problems to fix")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
