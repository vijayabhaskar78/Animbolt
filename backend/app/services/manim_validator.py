import ast
from dataclasses import dataclass


ALLOWED_IMPORT_ROOTS = {"manimlib", "manim", "math", "numpy", "random"}
BANNED_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "globals",
    "locals",
}
BANNED_ATTR_NAMES = {
    "system",
    "popen",
    "spawn",
    "fork",
    "remove",
    "unlink",
    "rmdir",
    "walk",
    "listdir",
}


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    error: str = ""


def validate_manim_code(code: str) -> ValidationResult:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return ValidationResult(ok=False, error=f"syntax error: {exc}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORT_ROOTS:
                    return ValidationResult(ok=False, error=f"import blocked: {alias.name}")

        if isinstance(node, ast.ImportFrom):
            if not node.module:
                return ValidationResult(ok=False, error="from-import missing module")
            root = node.module.split(".")[0]
            if root not in ALLOWED_IMPORT_ROOTS:
                return ValidationResult(ok=False, error=f"import blocked: {node.module}")

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BANNED_CALL_NAMES:
                return ValidationResult(ok=False, error=f"function blocked: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in BANNED_ATTR_NAMES:
                return ValidationResult(ok=False, error=f"attribute blocked: {node.func.attr}")

        if isinstance(node, ast.Attribute) and node.attr in {"__dict__", "__class__", "__bases__"}:
            return ValidationResult(ok=False, error=f"attribute blocked: {node.attr}")

    try:
        compile(code, "<generated_manim>", "exec")
    except Exception as exc:  # noqa: BLE001
        return ValidationResult(ok=False, error=f"compile failed: {exc}")

    return ValidationResult(ok=True)

