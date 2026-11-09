"""A small calculation-sheet builder.

Each design module writes its working into a Report step by step. The same
report is printed to the console and can be saved as a Markdown file, so the
console run and the submitted report always match. Output is plain ASCII so it
displays correctly on any lab computer terminal.
"""

from __future__ import annotations

import math
from pathlib import Path


def num(v: float | int | None, digits: int | None = None) -> str:
    """Readable number formatting for calculation sheets."""
    if v is None:
        return "-"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if math.isinf(v):
        return "inf"
    if math.isnan(v):
        return "nan"
    if digits is not None:
        return f"{v:.{digits}f}"
    a = abs(v)
    if a == 0:
        return "0"
    if a < 1e6 and v == round(v):
        return str(int(round(v)))          # 50.0 -> "50" (standard sizes, counts)
    if a >= 1e6 or a < 1e-3:
        return f"{v:.4g}"
    if a >= 100:
        return f"{v:.1f}"
    if a >= 1:
        return f"{v:.3f}"
    return f"{v:.4f}"


class Report:
    def __init__(self, title: str) -> None:
        self.title = title
        self.blocks: list[tuple] = []

    # ------------------------------------------------------------------ builders
    def heading(self, text: str) -> None:
        self.blocks.append(("heading", text))

    def text(self, text: str = "") -> None:
        self.blocks.append(("text", text))

    def calc(self, label: str, value, unit: str = "", expr: str = "", digits: int | None = None) -> None:
        value_str = value if isinstance(value, str) else num(value, digits)
        self.blocks.append(("calc", label, expr, value_str, unit))

    def check(self, ok: bool, text: str) -> None:
        self.blocks.append(("check", ok, text))

    def table(self, headers: list[str], rows: list[list]) -> None:
        str_rows = [[c if isinstance(c, str) else num(c) for c in r] for r in rows]
        self.blocks.append(("table", headers, str_rows))

    # ------------------------------------------------------------------ rendering
    @staticmethod
    def _calc_line(label: str, expr: str, value: str, unit: str) -> str:
        rhs = f"{expr} = {value}" if expr else value
        return f"  {label:<36} = {rhs} {unit}".rstrip()

    @staticmethod
    def _table_lines(headers: list[str], rows: list[list[str]]) -> list[str]:
        widths = [len(h) for h in headers]
        for r in rows:
            for i, c in enumerate(r):
                widths[i] = max(widths[i], len(c))
        fmt_row = lambda cells: "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)) + " |"
        out = [fmt_row(headers), "|" + "|".join("-" * (w + 2) for w in widths) + "|"]
        out += [fmt_row(r) for r in rows]
        return out

    def _body_line(self, block: tuple) -> str:
        kind = block[0]
        if kind == "text":
            return f"  {block[1]}" if block[1] else ""
        if kind == "calc":
            return self._calc_line(*block[1:])
        if kind == "check":
            tag = "[ OK ]" if block[1] else "[FAIL]"
            return f"  {tag} {block[2]}"
        raise ValueError(kind)

    def to_text(self) -> str:
        bar = "=" * max(60, len(self.title) + 4)
        out = [bar, f"  {self.title}", bar]
        for b in self.blocks:
            if b[0] == "heading":
                out += ["", b[1], "-" * len(b[1])]
            elif b[0] == "table":
                out += ["  " + line for line in self._table_lines(b[1], b[2])]
            else:
                out.append(self._body_line(b))
        return "\n".join(out) + "\n"

    def to_markdown(self) -> str:
        out = [f"# {self.title}", ""]
        in_fence = False
        for b in self.blocks:
            is_body = b[0] in ("text", "calc", "check")
            if is_body and not in_fence:
                out.append("```text")
                in_fence = True
            if not is_body and in_fence:
                out += ["```", ""]
                in_fence = False
            if b[0] == "heading":
                out += [f"## {b[1]}", ""]
            elif b[0] == "table":
                out += self._table_lines(b[1], b[2]) + [""]
            else:
                out.append(self._body_line(b))
        if in_fence:
            out.append("```")
        return "\n".join(out) + "\n"

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_markdown(), encoding="utf-8")
        return p
