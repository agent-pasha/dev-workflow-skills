---
name: create-ralph-prompt
description: |
  Create a session prompt file for iterative agent sessions (ralph loops) — one task per session, verified, committed, then the session ends and the loop restarts it.
  Generates a self-contained prompt in the specs directory that guides an agent through tasks one at a time with mandatory verification.
  Two modes: (1) prompt backed by an existing todo/plan file, (2) ad-hoc prompt with an inline goal where the skill creates a tracker file.
  Triggers: "create ralph prompt", "create a prompt for", "create session prompt", "/create-ralph-prompt", "write a loop prompt for"
---

# Session Prompt Generator

Generate a `specs/{name}-prompt.md` file that drives iterative one-task-at-a-time agent sessions. The prompt must be fully self-contained — an agent reading it cold should know exactly what to do, how to verify, and when to stop.

## Before you start: workflow context

This skill reads repo conventions from `.agents/workflow-context.md` at the git root. If that file is missing, or any section listed below is missing or still `TODO`, run the onboarding procedure in [references/onboarding.md](references/onboarding.md) first: infer from the repo, ask only what's left, write the file, then continue here.

**Context it needs:** `Specs & Docs` (specs directory) · `Gates` · `Local Environment` (verify-by-change-type) · `Tickets, Branches, Commits` (commit format) · `Autonomous Sessions` (agent CLI, non-interactive command, subagent budget).

Below, `specs/` means the context file's specs directory.

## Workflow

### 1. Determine the Mode

**Mode A — Todo/plan exists.** User specifies a todo list or plan file (e.g., `specs/migration-todo.md`, typically produced by the `implementation-plan` skill). The prompt will point to it. No tracker file needed.

**Mode B — Ad-hoc goal.** User describes a goal without a pre-existing plan (e.g., "fix the admin dashboard — it's not booting up locally"). Create a lightweight tracker file at `specs/{name}-tracker.md` so sessions can track progress, know what's been tried, and know when to stop. See "Tracker File Format" below.

If the mode is ambiguous, ask the user.

### 2. Gather Context

Ask the user only what's needed. Common questions (skip if already clear from the request or the context file):
- What area of the codebase is involved?
- Are there specific skills, tools, or services the agent should use?
- Are there verification requirements beyond the defaults? (e.g., must test via browser, must test via curl, must run specific test suite)
- Any constraints? (e.g., "don't modify the database schema", "only touch frontend code")

### 3. Write the Prompt

Output to `specs/{name}-prompt.md`. Follow the structure below, adapting sections to the domain. Fill the verification section from the context file's `Gates` and `Local Environment` tables for the areas involved. Remove sections that don't apply — shorter is better. An agent shouldn't have to read through irrelevant boilerplate.

### 4. Write the Tracker (Mode B only)

If no todo/plan exists, create `specs/{name}-tracker.md`. See format below.

---

## Prompt Structure

```markdown
# {Title} — Session Prompt

{1-2 lines: what to study first}
1. Study @specs/{plan-or-tracker-file}
2. Pick the most important incomplete task and implement it.

## Context

{2-5 sentences: what this work is about, what the current state is,
what "done" looks like. Enough for a cold-start agent to orient.}

## Workflow

- Pick the highest-priority incomplete task from the tracker.
- Implement it. Iterate until verification passes.
- Update the tracker with progress, decisions, and issues found.
- **ONE TASK PER SESSION**: Implement ONE task, verify it, update
  the tracker, commit (using the repo's commit format), and STOP.

### When a task is too large

1. Expand into atomic subtasks in the tracker.
2. Document findings (file paths, code snippets, what needs to change).
3. Commit the tracker update and STOP.

### When all tasks are done

{What to do when the tracker is empty — varies by project.
Examples: run comprehensive E2E test, do final verification pass,
report completion.}

## Verification (MANDATORY)

{Domain-specific verification requirements. Every prompt MUST have
this section. Tailor to the work, using the real commands from the
context file:}

- Unit tests alone are NOT sufficient — verify on the live environment.
- {Specific checks: curl commands, browser checks, log inspection, DB queries}
- If verification fails, debug and fix. Do not mark complete.
- If issues unrelated to the current task are found, document them in
  the tracker as new items — do not fix them in this session.

## Quality

- **Subagents**: Use up to {N, from the context file's budget} subagents for parallel work and research.
- {Any code style, testing, or documentation requirements}

## Technology & Docs

- {Relevant tools, skills, or documentation sources}

## Record Learnings

- If you discover useful information during implementation, add it to
  the tracker so future sessions can reference it.
```

## Tracker File Format (Mode B)

When the user provides an ad-hoc goal without a pre-existing plan, create a tracker that gives the agent enough context to orient and iterate:

```markdown
# {Title} — Progress Tracker

**Goal:** {One-sentence description of what "done" looks like}
**Created:** {date}
**Status:** In Progress

## Current Issues

- [ ] {Issue 1 — description, any known details}
- [ ] {Issue 2 — if multiple issues are already known}

## Completed

{Empty initially. Agent moves items here as they're resolved.}

## Session Log

{Empty initially. Agent appends a brief entry after each session:
what was attempted, what worked, what didn't, what to try next.}

## Learnings & Gotchas

{Empty initially. Agent adds discoveries here.}
```

The tracker intentionally starts minimal. The first session's job is often to investigate and expand the issue list. The "Session Log" section is what lets subsequent sessions avoid repeating failed approaches.

## Running the Loop

After generating the prompt, suggest how to run it, using the context file's `Non-interactive run` command and the relative path from project root to the prompt file. Each iteration starts a fresh session, so context never accumulates across tasks. Examples by agent CLI:

**Claude Code**

```bash
# Unsupervised (fully autonomous, loops until you kill it):
while true; do cat specs/{name}-prompt.md | claude --dangerously-skip-permissions -p ; done

# Supervised (interactive session each time — press Ctrl-C to stop, or let it continue):
while true; do cat specs/{name}-prompt.md | claude --dangerously-skip-permissions ; done
```

`-p` (print mode) makes Claude output results and exit without interactive prompts, which is what an unsupervised loop needs.

**Codex CLI**

```bash
while true; do codex exec --full-auto "$(cat specs/{name}-prompt.md)" ; done
```

**Other agents** — any CLI that accepts a prompt on stdin or as an argument and exits when done works the same way; check the context file.

Bound the loop when you can: add `sleep 5` between iterations, cap iterations with a counter, and stop the loop when the tracker's issue list is empty. A skip-permissions / full-auto flag hands the agent write and shell access — run it on a branch, in a worktree, or in a container.

## Key Principles

- **Self-contained.** An agent with zero prior context should be able to read the prompt and start working immediately.
- **One task per session.** Every prompt enforces this. It prevents context window exhaustion and makes progress incremental and reversible.
- **Mandatory verification.** Every prompt includes a verification section. "Looks correct" is never sufficient.
- **Shorter is better.** Only include sections relevant to the work. A prompt for "fix a CSS bug" doesn't need a message-queue SDK section. Remove what doesn't apply.
- **Domain-appropriate.** Match verification requirements, tools, and skills to the actual work. Don't copy-paste a Kubernetes verification section into a frontend prompt.
- **Tracker enables iteration.** For ad-hoc goals, the tracker is what gives continuity across sessions. Without it, each session starts from scratch.
