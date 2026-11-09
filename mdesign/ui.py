"""Console prompts with defaults and input checking.

Every prompt shows a default in [brackets]; pressing Enter accepts it. This keeps
a live demonstration quick while still letting the examiner type any values.
"""

from __future__ import annotations


class InputAborted(Exception):
    """Raised when the input stream closes (Ctrl-D / Ctrl-Z) during a prompt."""


def _read(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        print()
        raise InputAborted() from None


def _fmt_default(v) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def ask_float(prompt: str, default: float | None = None, unit: str = "", minimum: float | None = None,
              maximum: float | None = None, strictly_positive: bool = False) -> float:
    unit_txt = f" ({unit})" if unit else ""
    dflt = f" [{_fmt_default(default)}]" if default is not None else ""
    while True:
        raw = _read(f"  {prompt}{unit_txt}{dflt}: ").strip()
        if raw == "" and default is not None:
            return float(default)
        try:
            v = float(raw)
        except ValueError:
            print("    -> please enter a number")
            continue
        if strictly_positive and v <= 0:
            print("    -> must be greater than 0")
            continue
        if minimum is not None and v < minimum:
            print(f"    -> must be at least {minimum:g}")
            continue
        if maximum is not None and v > maximum:
            print(f"    -> must be at most {maximum:g}")
            continue
        return v


def ask_int(prompt: str, default: int | None = None, minimum: int | None = None,
            maximum: int | None = None) -> int:
    while True:
        v = ask_float(prompt, default, minimum=minimum, maximum=maximum)
        if v != int(v):
            print("    -> please enter a whole number")
            continue
        return int(v)


def ask_choice(prompt: str, options: list[tuple[str, str]], default: str | None = None) -> str:
    """options = [(key, description), ...]; the user may type the number or the key."""
    print(f"  {prompt}")
    for i, (key, desc) in enumerate(options, 1):
        mark = "  (default)" if key == default else ""
        print(f"     {i}) {desc}{mark}")
    keys = [k for k, _ in options]
    dflt = f" [{keys.index(default) + 1}]" if default in keys else ""
    while True:
        raw = _read(f"  Choice{dflt}: ").strip()
        if raw == "" and default in keys:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return keys[int(raw) - 1]
        for k in keys:
            if raw.lower() == k.lower():
                return k
        print(f"    -> enter a number from 1 to {len(options)}")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    dflt = "Y/n" if default else "y/N"
    while True:
        raw = _read(f"  {prompt} [{dflt}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("    -> please answer y or n")


def ask_text(prompt: str, default: str = "", allowed: list[str] | None = None) -> str:
    dflt = f" [{default}]" if default else ""
    while True:
        raw = _read(f"  {prompt}{dflt}: ").strip()
        if raw == "":
            raw = default
        if allowed is None or raw in allowed:
            return raw
        print(f"    -> must be one of: {', '.join(allowed)}")


def section(title: str) -> None:
    print()
    print(f"--- {title} " + "-" * max(0, 60 - len(title)))
