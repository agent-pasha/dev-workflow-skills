"""Shared helpers for reading Claude Code session transcripts (`<projects>/<project>/<session>.jsonl`)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# Text that arrives as a user message but was not typed by the person.
_SYSTEM_PREFIXES = (
    "<command-", "<local-command", "<bash-", "<task-notification", "<system-reminder",
    "[Request interrupted", "Caveat:",
)


def projects_root() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return Path(base) / "projects"


def session_files(folder: Path) -> list[Path]:
    """Top-level session transcripts under a folder. Subagent transcripts are excluded."""
    folder = Path(folder)
    if folder.is_file():
        return [folder]
    if (folder.parent / f"{folder.name}.jsonl").is_file():  # a session's own folder
        return [folder.parent / f"{folder.name}.jsonl"]
    direct = sorted(folder.glob("*.jsonl"))
    return direct or sorted(folder.glob("*/*.jsonl"))


def load_rows(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def human_text(row: dict) -> str | None:
    """The prompt text if this row is something the person typed, else None."""
    if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain") or row.get("isCompactSummary"):
        return None
    origin = row.get("origin") or {}
    if origin and origin.get("kind") != "human":
        return None
    content = (row.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    text = text_of(content)
    if not text.strip() and not (isinstance(content, list) and any(b.get("type") == "image" for b in content)):
        return None
    if text.lstrip().startswith(_SYSTEM_PREFIXES):
        return None
    return text


def normalize(s: str) -> str:
    """Lowercase and collapse whitespace and list markers, so pasted text matches the stored prompt."""
    s = s.lower()
    s = re.sub(r"(?m)^\s*([*\-•]|\d+[.)])\s+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def session_title(rows: list[dict]) -> str:
    custom = [r.get("customTitle") for r in rows if r.get("type") == "custom-title" and r.get("customTitle")]
    if custom:
        return custom[-1]
    ai = [r.get("aiTitle") for r in rows if r.get("type") == "ai-title" and r.get("aiTitle")]
    return ai[-1] if ai else ""


def repo_root(cwd: str) -> str:
    """The checkout a cwd belongs to, folding Claude Code worktrees back into their repo."""
    return re.sub(r"/\.claude/worktrees/[^/]+.*$", "", cwd or "")
