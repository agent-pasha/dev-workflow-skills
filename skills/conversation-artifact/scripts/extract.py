#!/usr/bin/env python3
"""Turn one Claude Code session transcript into the inputs for build.mjs.

Usage:
    python3 extract.py <session.jsonl> --out <work-dir>

Writes into <work-dir>:
    events.json   the conversation as an ordered event list (prompts, replies, decisions,
                  tool activity, agent events, markers)
    images/       images the person attached, in order (img1, img2, ...)
    review.md     every text that will be published, for reading before publishing
    scan.txt      secret-shaped strings found in that text, with context
    meta.json     page metadata with defaults; never overwritten, so edits survive a re-run

Events follow file order, which is the order the conversation happened in. Tool outputs and
the agent's thinking are not extracted; tool calls keep only their name and a short label.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True  # keep the installed skill directory clean
sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcript import load_rows, repo_root, session_title, text_of  # noqa: E402

SECRET_PATTERNS = {
    "api key (sk-)": r"sk-[A-Za-z0-9_\-]{16,}",
    "github token": r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}",
    "slack token": r"xox[abprs]-[\w-]{10,}",
    "aws key": r"AKIA[0-9A-Z]{16}",
    "stripe/clerk key": r"\b[prs]k_(test|live)_[A-Za-z0-9]{10,}",
    "webhook secret": r"whsec_\w+",
    "google key": r"AIza[0-9A-Za-z_\-]{30,}",
    "jwt": r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}",
    "private key": r"BEGIN [A-Z ]*PRIVATE KEY",
    "url with password": r"://[^/\s:@]+:[^/\s@]+@",
    "bearer token": r"(?i)bearer\s+[A-Za-z0-9\-_.]{15,}",
    "assignment": r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]{6,}",
    "long hex": r"\b[a-f0-9]{40,}\b",
}


def model_name(model_id: str) -> str:
    m = re.match(r"claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?$", model_id or "")
    if not m:
        return model_id or ""
    return f"{m.group(1).capitalize()} {m.group(2)}{'.' + m.group(3) if m.group(3) else ''}"


def make_rel(rows: list[dict]):
    roots = {repo_root(r["cwd"]) for r in rows if r.get("cwd")}
    roots |= {m.group(0) for r in rows if r.get("cwd") for m in [re.match(r".*/\.claude/worktrees/[^/]+", r["cwd"])] if m}
    prefixes = sorted((p.rstrip("/") + "/" for p in roots if p), key=len, reverse=True)
    home = os.path.expanduser("~")

    def rel(p: str) -> str:
        if not p:
            return ""
        for pre in prefixes:
            if p.startswith(pre):
                return p[len(pre):]
        return p.replace(home, "~", 1) if p.startswith(home) else p

    return rel


def tool_label(b: dict, rel) -> tuple[str, str]:
    n, i = b.get("name", ""), b.get("input") or {}
    if n == "Bash":
        return "Shell", i.get("description") or (i.get("command") or "")[:80]
    if n in ("Read", "Edit", "Write", "NotebookEdit", "MultiEdit"):
        return n, rel(i.get("file_path") or i.get("notebook_path") or "")
    if n in ("Grep", "Glob"):
        return n, i.get("pattern", "")
    if n in ("Agent", "Task"):
        return "Subagent", " ".join(x for x in (i.get("description", ""), f"({i['subagent_type']})" if i.get("subagent_type") else "") if x)
    if n == "Workflow":
        s = i.get("script") or ""
        m = re.search(r"description:\s*(['\"`])(.*?)\1", s, re.S) or re.search(r"name:\s*(['\"`])(.*?)\1", s, re.S)
        return "Workflow", ((m.group(2) if m else "") or i.get("name") or "") + (" (resumed)" if i.get("resumeFromRunId") else "")
    simple = {"Skill": ("Skill", "skill"), "WebFetch": ("Web fetch", "url"), "WebSearch": ("Web search", "query"),
              "ToolSearch": ("Load tools", "query"), "TaskStop": ("Stop task", "task_id"), "Artifact": ("Artifact", "action"),
              "DesignSync": ("Design sync", "action"), "SendMessage": ("Message agent", "to")}
    if n in simple:
        label, key = simple[n]
        return label, str(i.get(key, "") or "")
    if n == "RemoteTrigger":
        body = i.get("body") if isinstance(i.get("body"), dict) else {}
        return "Routine", " ".join(x for x in (i.get("action", ""), i.get("name") or body.get("name", "")) if x)
    if n.startswith("mcp__"):
        parts = n.split("__")
        server = re.sub(r"^claude_ai_|^plugin_[^_]+_", "", parts[1]).replace("_", " ")
        op = parts[-1].replace("_", " ")
        target = next((str(i[k]) for k in ("title", "id", "issueId", "name", "query", "url") if i.get(k)), "")
        return server or "MCP", f"{op}: {target}" if target else op
    return n, ""


def save_image(block: dict, n: int, img_dir: Path) -> dict:
    src = block.get("source") or {}
    mime = src.get("media_type", "image/png")
    ext = mime.split("/")[-1].replace("jpeg", "jpg")
    path = img_dir / f"img{n}.{ext}"
    path.write_bytes(base64.b64decode(src.get("data", "")))
    # Shrink large screenshots so the page stays light; sips ships with macOS.
    if path.stat().st_size > 200_000 and shutil.which("sips"):
        small = img_dir / f"img{n}.jpg"
        r = subprocess.run(["sips", "-Z", "900", "-s", "format", "jpeg", "-s", "formatOptions", "70", str(path), "--out", str(small)],
                           capture_output=True)
        if r.returncode == 0 and small.exists():
            if small != path:
                path.unlink()
            path, mime = small, "image/jpeg"
    return {"id": f"img{n}", "file": f"images/{path.name}", "mime": mime}


def extract(rows: list[dict], img_dir: Path) -> list[dict]:
    rel = make_rel(rows)
    ask_inputs, ask_results = {}, {}
    for d in rows:
        if d.get("type") == "assistant":
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "AskUserQuestion":
                    ask_inputs[b["id"]] = b.get("input") or {}
    for d in rows:
        content = (d.get("message") or {}).get("content")
        if d.get("type") == "user" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in ask_inputs:
                    t = d.get("toolUseResult") if isinstance(d.get("toolUseResult"), dict) else {}
                    ask_results[b["tool_use_id"]] = {"answers": t.get("answers") or {}, "annotations": t.get("annotations") or {}}

    events: list[dict] = []
    activity: dict | None = None

    def flush():
        nonlocal activity
        if activity and activity["items"]:
            events.append(activity)
        activity = None

    def push(ev: dict):
        flush()
        events.append(ev)

    img_n = 0
    for d in rows:
        t, ts = d.get("type"), d.get("timestamp")
        if d.get("isSidechain"):
            continue
        if t == "assistant":
            for b in (d.get("message") or {}).get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    push({"k": "assistant", "ts": ts, "text": b["text"]})
                elif b.get("type") == "tool_use":
                    if b.get("name") == "AskUserQuestion":
                        a = ask_results.get(b["id"], {})
                        push({"k": "ask", "ts": ts, "questions": (b.get("input") or {}).get("questions", []),
                              "answers": a.get("answers", {}), "annotations": a.get("annotations", {})})
                        continue
                    if activity is None:
                        activity = {"k": "activity", "ts": ts, "items": []}
                    tool, label = tool_label(b, rel)
                    activity["items"].append({"tool": tool, "label": label})
        elif t == "user":
            content = (d.get("message") or {}).get("content")
            origin = d.get("origin") or {}
            text = text_of(content)
            if d.get("isCompactSummary"):
                i = text.find("This session is being continued")
                push({"k": "compact", "ts": ts, "text": text[i:] if i >= 0 else text})
                continue
            if origin.get("kind") == "task-notification" or text.lstrip().startswith("<task-notification>"):
                g = lambda tag: (re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S) or [None, ""])[1]  # noqa: E731
                push({"k": "notify", "ts": ts, "status": g("status"), "summary": g("summary"), "result": g("result")})
                continue
            if origin.get("kind") == "peer":
                body = (origin.get("body") or "").split("The report follows:\n", 1)[-1]
                body = re.sub(r"^\s*\[harness:[^\n]*\]\n", "", body)
                push({"k": "handback", "ts": ts, "text": textwrap.dedent(body).strip()})
                continue
            if d.get("isMeta"):
                continue
            if isinstance(content, list) and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                continue
            imgs = []
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "image":
                        img_n += 1
                        imgs.append(save_image(b, img_n, img_dir))
            s = text.strip()
            if m := re.search(r"<command-name>(.*?)</command-name>", s):
                push({"k": "command", "ts": ts, "name": m.group(1), "out": ""})
                continue
            if m := re.search(r"<bash-input>(.*?)</bash-input>", s, re.S):
                push({"k": "command", "ts": ts, "name": "! " + m.group(1).strip()[:200], "out": ""})
                continue
            if m := re.search(r"<(local-command-stdout|bash-stdout|bash-stderr)>(.*?)</\1>", s, re.S):
                out = m.group(2).strip()
                if events and events[-1]["k"] == "command" and out and out != "(no content)":
                    events[-1]["out"] = (events[-1]["out"] + "\n" + out).strip()[:600]
                continue
            if s.startswith("[Request interrupted"):
                push({"k": "interrupt", "ts": ts, "text": s.strip("[]")})
                continue
            if s.startswith(("<local-command-caveat", "<system-reminder", "Caveat:")):
                continue
            if origin.get("kind") in (None, "human"):
                push({"k": "human", "ts": ts, "text": text, "imgs": imgs, "source": d.get("promptSource")})
        elif t == "system" and d.get("subtype") == "compact_boundary":
            push({"k": "boundary", "ts": ts, "meta": (d.get("compactMetadata") or {}).get("preTokens")})
        elif t == "system" and d.get("subtype") == "away_summary":
            push({"k": "away", "ts": ts, "text": re.sub(r"\s*\(disable recaps in /config\)\s*$", "", d.get("content", ""))})
        elif t == "pr-link":
            if not any(e["k"] == "pr" and e["number"] == d.get("prNumber") for e in events):
                push({"k": "pr", "ts": ts, "number": d.get("prNumber"), "url": d.get("prUrl"), "repo": d.get("prRepository")})
    flush()

    # Merge each compaction boundary into the summary that follows it.
    merged = []
    for e in events:
        if e["k"] == "compact" and merged and merged[-1]["k"] == "boundary":
            e["pre"] = merged.pop()["meta"]
        merged.append(e)
    merged = [e for e in merged if e["k"] != "boundary"]
    # Drop stray notifications that arrive after the last reply (a later resume of the session).
    last = max((i for i, e in enumerate(merged) if e["k"] == "assistant"), default=len(merged) - 1)
    return [e for i, e in enumerate(merged) if i <= last or e["k"] not in ("notify", "pr")]


def published_texts(e: dict):
    for k in ("text", "summary", "result", "out", "name"):
        if isinstance(e.get(k), str):
            yield e[k]
    for it in e.get("items", []):
        yield it["label"]
    if e["k"] == "ask":
        yield json.dumps(e["questions"], ensure_ascii=False)
        yield json.dumps(e["answers"], ensure_ascii=False)
        yield json.dumps(e["annotations"], ensure_ascii=False)


def write_review(events: list[dict], path: Path):
    out = []
    for i, e in enumerate(events):
        if e["k"] == "human":
            out.append(f"\n## [{i}] PROMPT {e['ts']}\n{e['text']}" + (f"\n(images: {', '.join(x['id'] for x in e['imgs'])})" if e["imgs"] else ""))
        elif e["k"] == "assistant":
            out.append(f"\n## [{i}] REPLY {e['ts']}\n{e['text']}")
        elif e["k"] == "ask":
            for q in e["questions"]:
                out.append(f"\n## [{i}] DECISION {q.get('header', '')}: {q.get('question', '')}\nanswer: {e['answers'].get(q.get('question'), '')}")
        elif e["k"] in ("handback", "compact"):
            out.append(f"\n## [{i}] {e['k'].upper()} {e['ts']}\n{e['text']}")
        elif e["k"] == "notify":
            out.append(f"\n## [{i}] NOTIFY {e['summary']}\n{e['result'][:4000]}")
        elif e["k"] == "activity":
            out.append(f"\n## [{i}] TOOLS\n" + "\n".join(f"- {it['tool']}: {it['label']}" for it in e["items"]))
        elif e["k"] in ("command", "interrupt", "away", "pr"):
            out.append(f"\n## [{i}] {e['k'].upper()} {e.get('name') or e.get('text') or e.get('url', '')} {e.get('out', '')}")
    path.write_text("\n".join(out), encoding="utf-8")


def write_scan(events: list[dict], path: Path) -> int:
    hits = []
    for i, e in enumerate(events):
        for text in published_texts(e):
            for name, pat in SECRET_PATTERNS.items():
                for m in re.finditer(pat, text):
                    s = max(0, m.start() - 60)
                    hits.append(f"[{i}] {e['k']} {name}: {text[s:m.end() + 40]!r}")
    path.write_text("\n".join(hits) + ("\n" if hits else ""), encoding="utf-8")
    return len(hits)


def default_meta(rows: list[dict], events: list[dict]) -> dict:
    cwds = Counter(repo_root(r["cwd"]) for r in rows if r.get("cwd"))
    project = os.path.basename(cwds.most_common(1)[0][0]) if cwds else ""
    models = Counter((r.get("message") or {}).get("model") for r in rows if r.get("type") == "assistant")
    models.pop(None, None)
    models.pop("<synthetic>", None)
    model = model_name(models.most_common(1)[0][0]) if models else ""
    try:
        user = subprocess.run(["git", "config", "--global", "user.name"], capture_output=True, text=True).stdout.split()[0]
    except (IndexError, OSError):
        user = (os.environ.get("USER") or "You").capitalize()
    return {
        "title": session_title(rows) or "TODO: a two-to-four word name",
        "description": "TODO: one sentence for the gallery card",
        "eyebrow": " · ".join(x for x in ("Claude Code session", project, model) if x),
        "dek": "TODO: one or two sentences on what the conversation was and where it went",
        "outcome": "TODO: markdown, one or two sentences on where it ended, with links; or empty to omit",
        "userName": user,
        "agentName": "Claude",
        "agentNoun": "Claude",
        "timezone": "",
        "imageAlts": {x["id"]: "TODO: describe the image" for e in events if e["k"] == "human" for x in e["imgs"]},
        "redactions": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcript", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    rows = load_rows(args.transcript)
    args.out.mkdir(parents=True, exist_ok=True)
    img_dir = args.out / "images"
    if img_dir.exists():
        shutil.rmtree(img_dir)
    img_dir.mkdir()

    events = extract(rows, img_dir)
    (args.out / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=0), encoding="utf-8")
    write_review(events, args.out / "review.md")
    n_hits = write_scan(events, args.out / "scan.txt")
    meta_path = args.out / "meta.json"
    kept_meta = meta_path.exists()
    if not kept_meta:
        meta_path.write_text(json.dumps(default_meta(rows, events), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kinds = Counter(e["k"] for e in events)
    tools = sum(len(e["items"]) for e in events if e["k"] == "activity")
    review_chars = (args.out / "review.md").stat().st_size
    print(f"events: {dict(kinds)}; tool actions: {tools}")
    print(f"review.md: {review_chars:,} bytes to read before publishing")
    print(f"scan.txt: {n_hits} secret-shaped hit(s)")
    print(f"meta.json: {'kept existing' if kept_meta else 'written with defaults; fill in every TODO'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
