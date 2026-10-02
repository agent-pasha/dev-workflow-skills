#!/usr/bin/env python3
"""Find a Claude Code session transcript by what was said in it, or list the sessions in a folder.

Usage:
    python3 find_session.py "text the conversation starts with"    # search every project
    python3 find_session.py "text" --folder <dir-or-file>           # search one folder
    python3 find_session.py --list [--folder <dir>] [--limit 20]    # newest sessions first
    add --json for machine-readable output, --anywhere to also match the agent's replies

The default root is $CLAUDE_CONFIG_DIR/projects or ~/.claude/projects. Only top-level session
files are searched; subagent transcripts are skipped. Results are ranked:
  starts   the first prompt starts with the text
  first    the first prompt contains it
  later    a later prompt contains it
  reply    only an agent reply contains it (with --anywhere)
A session written to in the last two minutes is flagged ACTIVE: that is usually the session
running this search, because the request quotes the text. Skip it unless the person means it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # keep the installed skill directory clean
sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcript import human_text, load_rows, normalize, projects_root, repo_root, session_files, session_title, text_of  # noqa: E402

RANK = {"starts": 4, "first": 3, "later": 2, "reply": 1}


def summarize(path: Path, needles: list[str], anywhere: bool) -> dict | None:
    rows = load_rows(path)
    prompts = [(r.get("timestamp"), t) for r in rows if (t := human_text(r)) is not None]
    stamps = [r.get("timestamp") for r in rows if r.get("timestamp") and r.get("type") in ("user", "assistant")]
    if not stamps:
        return None
    cwd = next((r.get("cwd") for r in rows if r.get("cwd")), "")
    info = {
        "path": str(path),
        "session": path.stem,
        "title": session_title(rows),
        "project": os.path.basename(repo_root(cwd)) or path.parent.name,
        "cwd": cwd,
        "start": min(stamps),
        "end": max(stamps),
        "prompts": len(prompts),
        "first_prompt": (prompts[0][1] if prompts else "").strip()[:160],
        "active": time.time() - path.stat().st_mtime < 120,
        "match": None,
    }
    if not needles:
        return info
    norm_prompts = [normalize(t) for _, t in prompts]
    for needle in needles:
        if norm_prompts and norm_prompts[0].startswith(needle):
            info["match"] = "starts"
        elif norm_prompts and needle in norm_prompts[0]:
            info["match"] = "first"
        elif any(needle in p for p in norm_prompts[1:]):
            info["match"] = "later"
        elif anywhere and any(
            needle in normalize(text_of((r.get("message") or {}).get("content"))) for r in rows if r.get("type") == "assistant"
        ):
            info["match"] = "reply"
        if info["match"]:
            info["matched_on"] = needle[:80]
            return info
    return None


def needles_for(query: str) -> list[str]:
    """Try the whole text first, then its opening, then its longest line, so small paste differences still match."""
    q = normalize(query)
    lines = sorted((normalize(l) for l in query.splitlines() if len(l.strip()) > 20), key=len, reverse=True)
    out = [q, q[:200], q[:80]] + lines[:1]
    return [n for i, n in enumerate(out) if n and n not in out[:i]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--folder", type=Path, default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--anywhere", action="store_true")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    folder = args.folder or projects_root()
    if not folder.exists():
        print(f"not found: {folder}", file=sys.stderr)
        return 1
    files = session_files(folder) if args.folder else sorted(folder.glob("*/*.jsonl"))
    needles = [] if args.list or not args.query else needles_for(args.query)
    if not needles and not args.list:
        ap.error("give the text to search for, or --list")

    results = [r for f in files if (r := summarize(f, needles, args.anywhere))]
    if needles:
        # Best match first, newest first within a rank; the active session last, since it is usually this search.
        results.sort(key=lambda r: (not r["active"], RANK[r["match"]], r["end"]), reverse=True)
    else:
        results.sort(key=lambda r: r["end"], reverse=True)
    results = results[: args.limit]

    if args.json:
        print(json.dumps(results, indent=1))
        return 0 if results else 1
    if not results:
        print("no matching sessions")
        return 1
    for r in results:
        when = datetime.fromisoformat(r["start"].replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
        tags = " ".join(t for t in ((f"[{r['match']}]" if r["match"] else ""), ("ACTIVE" if r["active"] else "")) if t)
        print(f"{tags} {when}  {r['project']}  {r['prompts']} prompts  {r['title']}".strip())
        print(f"    {r['path']}")
        print(f"    first prompt: {r['first_prompt'][:120]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
