---
name: conversation-artifact
description: >
  Turn a Claude Code conversation into a shareable artifact page: every prompt and every agent reply
  in order, the decisions the agent asked for with the answers given, tool activity and subagent or
  workflow events collapsed in between, and a prompt index to jump around. Works from a transcript
  path or folder the person gives, or finds the session by searching ~/.claude/projects for text they
  quote. Every page uses the same template, so pages look and read the same.
  Triggers on: "make an artifact of this conversation", "find the conversation that starts with …",
  "share session X as a page", "turn this transcript into an artifact", "I need to follow the
  conversation from start to end", "/conversation-artifact".
---

# Conversation Artifact

The page lets someone who wasn't there follow a session from the first prompt to the last reply. It shows exactly what the person typed and what the agent answered. It never shows the agent's private reasoning or raw tool output; tool calls appear only as their name and a one-line description.

This skill does not read `.agents/workflow-context.md`, so it needs no onboarding. It needs `python3` and Node 18 or newer. The Markdown renderer (marked 15.0.12) is vendored under `scripts/vendor/`, so nothing is installed and nothing is fetched.

`<skill>` below means this skill's directory. Work in a scratch directory (`<work>`), never in the person's repo.

## 1. Find the transcript

Claude Code stores each session as `<root>/<project>/<session-id>.jsonl`. `<root>` is `$CLAUDE_CONFIG_DIR/projects`, or `~/.claude/projects` by default. `<project>` is the session's working directory with `/` and `.` replaced by `-`; for example, `/Users/me/projects/app` becomes `-Users-me-projects-app`. Subagent transcripts live in `<session-id>/subagents/` and are never the conversation itself.

- **They give a `.jsonl` file:** use it.
- **They give a folder:** run `python3 <skill>/scripts/find_session.py --list --folder <dir>`. If it lists more than one session and their words don't single one out, show the list (date, title, prompt count, first prompt) and ask which one.
- **They ask you to find one:** search for a distinctive sentence or two from what they quoted, not the whole paste:

  ```bash
  python3 <skill>/scripts/find_session.py "Set up a worktree for this project and overhaul the dev environment"
  ```

  Matching ignores case, whitespace and list markers. Results rank as `starts` (the first prompt starts with the text), then `first` (the first prompt contains it), then `later` (a later prompt contains it). Add `--anywhere` to also search the agent's replies, and `--folder ~/.claude/projects/<project>` to stay in one project.
- **They mean the current conversation:** it is the session flagged `ACTIVE`. Say that the page ends at the moment you build it.

A session flagged `ACTIVE` was written to in the last two minutes. When you are searching for a different conversation, that is usually your own session, because the request quotes the text. Skip it. If two or more candidates remain after that, ask; don't guess.

## 2. Extract

```bash
python3 <skill>/scripts/extract.py <session.jsonl> --out <work>/<session-id>
```

It writes `events.json` (the conversation in file order), `images/` (attached images, with large screenshots shrunk on macOS), `review.md`, `scan.txt` and `meta.json`. A re-run keeps an existing `meta.json`.

## 3. Read everything before publishing

Publishing hands the content to whoever gets the link, so read it first. This step is not optional, even when the person says it's fine.

- Read `review.md` from start to end. It holds every text the page will show. For a large session, read it in chunks; don't skim or sample.
- View every file in `images/`.
- Go through each hit in `scan.txt`. Local development values (a `localhost` database URL, a seeded test password, a fake key for a local emulator) can stay. Real tokens, keys, production credentials, private personal data, and anything the person asked to keep out go into `meta.json` → `redactions` as exact strings; the build replaces each one with `[redacted]` everywhere. Ask when you can't tell whether something is safe.

If the session was rewound, abandoned attempts appear in file order. You'll see them as repeated or near-duplicate prompts in `review.md`. Tell the person rather than silently dropping them.

## 4. Fill in `meta.json`

| Field | What to write |
|---|---|
| `title` | A two-to-four word name for the page (it becomes the `<title>`, the heading and the gallery name). A name, never "Name: explanation". Use the person's name for the work if they have one. |
| `description` | One sentence for the gallery card. |
| `eyebrow` | Defaults to "Claude Code session · project · model". Change it only if it's wrong. |
| `dek` | One or two plain sentences: whose conversation, what it was about, and how far it got. |
| `outcome` | Markdown: one or two sentences on where it ended, with links (PRs, docs, artifacts) taken from the conversation. Use `""` to leave it out. Every fact must appear in `review.md`. |
| `userName` | How the person appears ("Sam wrote", "Sam ran"). Defaults to the first word of `git config user.name`. |
| `agentName`, `agentNoun` | `"Claude"`, `"Claude"` by default. Use `"Orchestrator"`, `"orchestrator"` when the agent mostly led subagents and workflows. |
| `timezone` | The person's IANA zone, such as `America/Los_Angeles`. Empty means this machine's zone. |
| `imageAlts` | One short description per image id of what the image shows. |
| `redactions` | Exact strings to replace with `[redacted]`. |

The build refuses to run while any field still contains `TODO`.

## 5. Build, look once, publish

```bash
node <skill>/scripts/build.mjs <work>/<session-id>
```

It writes `<work>/<session-id>/<title-slug>.html` (the page) and `preview.html` (the same page as a full document). For one look, take a screenshot of `preview.html` (headless Chrome: `--headless=new --screenshot=<png> --window-size=1400,2200 file://<preview.html>`). Fix only what is visibly broken, rebuild, and move on; don't loop.

Publish the page with the Artifact tool: `file_path` = the built page, `icon` = `chat`, `description` = `meta.description`. The template is the design, so don't redesign it per conversation. If the harness asks for a design pass before a first publish, do it, and keep the template as it is. To update the page later, rebuild and publish the same file path, which keeps the URL. Without an Artifact tool, hand over the file path; `preview.html` opens in any browser.

Then tell the person:
- the link;
- what the page includes and leaves out (reasoning and tool output are never shown);
- what you redacted, if anything;
- that the page starts private: others can open it only after it's shared from the page's Share menu.

## What the page contains

- **Header:** the title, eyebrow and dek, then one line of facts: time span, prompt count, reply count, decision rounds, workflows and subagents, tool actions. The outcome line and a note on what's included follow.
- **Prompt index:** every prompt, numbered, with its time. It is pinned on the left on wide screens and folds into "Show" on phones. The prompt in view is highlighted.
- **Log,** with day separators:
  - **Prompts:** highlighted; tagged "sent while the agent was working" when queued mid-turn; attached images inline.
  - **Agent replies:** rendered Markdown.
  - **Decisions:** every option, with the chosen one marked and any typed answer shown.
  - **Collapsed:** each run of tool calls, workflow, subagent and background-task completions (with their returned result), subagent reports, the summary from a context compaction, slash commands, interruptions and recaps.
- **Show toggles:** "Tool activity" and "Agent events" hide the collapsed rows, leaving only the dialogue.

The page is self-contained: one HTML file with images inlined and Google Fonts as the only external request. It handles light and dark themes and works at phone width.

## Changing the template

`assets/template.html` holds the page's CSS, header markup and script; `scripts/build.mjs` renders each kind of event. Change them only to improve every future page, and rebuild an existing page to check the change against a real session, both at phone width and on desktop. The `{{…}}` placeholders in the template are filled by `build.mjs`.

## Scripts

- `scripts/find_session.py`: search or list sessions. `--json` gives machine-readable output.
- `scripts/extract.py`: transcript → `events.json`, `images/`, `review.md`, `scan.txt`, `meta.json`.
- `scripts/build.mjs`: work dir → page. `--draft` builds even with `TODO` values left, for a look.
- `scripts/transcript.py`: transcript parsing shared by the first two.
