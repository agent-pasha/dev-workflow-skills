#!/usr/bin/env python3
"""Strip every `<<<<<<< HEAD ... ======= ... >>>>>>>` block down to the HEAD side.

Use only after manually confirming that "HEAD wins" is the correct resolution
for every conflict in the target file(s) — see references/legacy-train-conflicts.md
for the when-to-use guidance.

Usage:
    python3 <path-to-this-skill>/scripts/resolve_head_wins.py <path> [<path> ...]

Prints, for each path, the number of conflict blocks that were collapsed.

Tolerates LF and CRLF line endings, and a missing trailing newline at EOF
after the closing `>>>>>>>` marker.
"""

from __future__ import annotations

import re
import sys

# `\r?\n` so CRLF and LF both match; `(?:\r?\n|\Z)` after the closing marker
# so a conflict that sits at end-of-file (no trailing newline) still resolves.
_CONFLICT_RE = re.compile(
    r"<<<<<<< HEAD\r?\n(.*?)=======\r?\n.*?>>>>>>> [^\r\n]+(?:\r?\n|\Z)",
    re.DOTALL,
)


def resolve(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new_text, n = _CONFLICT_RE.subn(r"\1", text)
    if n:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
    return n


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: python3 resolve_head_wins.py <path> [<path> ...]",
            file=sys.stderr,
        )
        return 2
    for path in argv[1:]:
        n = resolve(path)
        print(f"{path}: resolved {n} conflict block(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
