---
name: implementation-plan
description: |
  Create a detailed implementation plan with atomic, bite-sized tasks ready for an autonomous one-task-per-session loop (a "ralph loop").
  Produces a progress-tracking todo list in the specs directory with tasks referencing specific code files and line numbers.
  Handles two modes: (1) plan from an existing research document, (2) plan from scratch by scouting the codebase with subagents.
  Triggers: "implementation plan", "create implementation plan", "plan implementation for", "/implementation-plan", "create a todo list for", "plan the work for"
---

# Implementation Plan Generator

Produce a markdown implementation plan in the specs directory with atomic, verification-backed tasks ready for execution in a one-task-per-session loop. Each task is bite-sized: implement one thing, verify it works, move on.

## Before you start: workflow context

This skill reads repo conventions from `.agents/workflow-context.md` at the git root. If that file is missing, or any section listed below is missing or still `TODO`, run the onboarding procedure in [references/onboarding.md](references/onboarding.md) first: infer from the repo, ask only what's left, write the file, then continue here.

**Context it needs:** `Repository` (areas) · `Specs & Docs` (specs directory) · `Gates` (test/lint/typecheck commands per area) · `Local Environment` (start command, verify-by-change-type) · `Autonomous Sessions` (subagent budget, reference implementations).

Below, `specs/` means the context file's specs directory, and every verification command comes from its `Gates` and `Local Environment` sections.

## Workflow

### 1. Clarify Requirements

Before any planning, ensure the goal is unambiguous. Ask the user clarifying questions if:
- The scope is vague ("improve the API" — which parts? what's the acceptance criteria?)
- There are multiple valid approaches and user preference matters
- Requirements have implicit assumptions that need confirming
- The definition of "done" is unclear

Interview the user with focused questions until mentally aligned. Do not proceed with ambiguity — a bad plan wastes more time than a few questions.

### 2. Determine Research Source

Check whether a research document already exists:

**User pointed to a specific research doc** — Read it and use as the primary reference. Proceed to step 3.

**Research doc exists but user didn't mention it** — Check `specs/` for relevant `*-research.md` files. If found, check the date:
- If < 3 days old: Ask user "I found `specs/X-research.md` from [date]. Should I base the plan on this?"
- If >= 3 days old: Ask user "I found `specs/X-research.md` from [date] — it may be outdated. Should I use it as-is, re-validate with a quick codebase check, or start fresh?"

**No research doc exists** — Proceed to step 2b (codebase scouting).

### 2b. Scout the Codebase (No Research Doc)

Launch subagents (scale with complexity, within the context file's budget) to investigate the codebase areas relevant to the goal. Each agent should:
- Search for specific files, patterns, and existing implementations
- Read relevant source code and tests
- Note TODOs, FIXMEs, placeholders, and minimal implementations
- Return findings with specific file paths (relative to project root) and line numbers

Example agent assignments for "add auth to internal endpoints":
- Agent 1: Inventory all internal endpoint files and their current auth status
- Agent 2: Read the existing auth dependency functions and patterns
- Agent 3: Check existing tests for auth enforcement patterns
- Agent 4: Read the reference implementation for comparison (if the context file lists one and this is a migration)
- Agent 5: Search for TODOs and known gaps related to auth

If your agent has no subagent support, do the same investigations sequentially. Wait for all findings before planning.

### 3. Structure the Plan

Group tasks into **phases** ordered by priority/dependency:
- Phase 1: Critical / blocking tasks
- Phase 2: Important but non-blocking
- Phase 3: Nice-to-have / cleanup

Within each phase, group related tasks into **sections** (e.g., "Auth Enforcement", "Scheduled Jobs").

### 4. Write Atomic Tasks

Each task must be:

**Self-contained** — Implementable in one focused step without needing to read the full plan for context.

**Specific** — Reference exact files (relative paths), functions, classes, line numbers. No vague "update the service" — say which service, which method, what change.

**Verifiable** — Every task ends with concrete verification steps, using the repo's real commands from the context file. Choose from:
- Unit test: `<area test command> path/to/test.py::test_name` — describe what the test asserts
- Integration test: curl command with expected response
- Local env check: `<local start command>` → observe behavior (note if fresh state is needed first)
- DB query: specific SQL to confirm state change
- Grep/search: confirm no remaining references, no regressions
- Full suite: `<full suite command>` — all tests still pass

**Ordered** — Tasks within a section build on each other. Later tasks may depend on earlier ones completing.

### 5. Write the Document

Output to `specs/{topic}-todo.md` with this structure:

```markdown
# {Title}: Implementation Todo List

**Date:** {today}
**Status:** Active progress tracker
**Source:** {link to research doc or "codebase investigation"}

---

## How to Use This Document

Each task is bite-sized: implement -> verify -> done. A task is only
marked `[x]` after ALL verification steps pass.

{Any environment setup notes relevant to this project — from the context file's Local Environment section}

**Legend:** `[ ]` = pending, `[x]` = done, `[~]` = in progress

---

## Phase 1: {Phase Name}

### 1.1 {Section Name}
**Ref:** {link to research gap or investigation finding}

{1-2 sentence context for why this section exists}

- [ ] **1.1.1** {Imperative task description}
  - Files: `path/to/file.py` (lines X-Y)
  - Verify: {specific verification step}
  - Verify: {second verification step if needed}
- [ ] **1.1.2** {Next task}
  - Files: `path/to/file.py`, `path/to/test.py`
  - Verify: {verification}

...

## Progress Summary

| Phase | Total | Done | Remaining |
|-------|-------|------|-----------|
| Phase 1 | N | 0 | N |
| Phase 2 | N | 0 | N |
| **Total** | **N** | **0** | **N** |

Last updated: {today}
```

### 6. Create Detail Specs for Complex Sections (Optional)

If a section has more than 5 tasks or involves non-obvious implementation, create a companion spec at `specs/gap-NN-{topic}.md` with:
- Problem description and context
- Reference code (existing implementation or comparison target)
- Proposed implementation with code snippets
- Full verification checklist

Link these from the main todo document.

### 7. Present and Confirm

Show the user:
- Total task count and phase breakdown
- Any assumptions made during planning
- How to execute it: the recommended path is the `create-ralph-prompt` skill, which turns this todo into a self-contained session prompt and gives the loop command for the repo's agent CLI. (If Claude Code's ralph-loop plugin is installed, `/ralph-loop "Work through specs/{topic}-todo.md tasks in order. Mark each [x] when done." --completion-promise "All tasks complete"` also works.)

Ask if any tasks need adjustment before starting the loop.

## Principles

- **Atomic over ambitious.** A task that takes 5 minutes and can be verified is better than one that takes 30 minutes and might break things.
- **Relative paths only.** Always `path/to/file.py`, never `/Users/foo/project/path/to/file.py`.
- **Verification is not optional.** Every task must have at least one concrete verification step. "It should work" is not verification.
- **Reference real code.** Every task should trace to specific files. If you can't name the file, you haven't planned enough.
- **Order matters for the loop.** Tasks are executed sequentially. Earlier tasks must not depend on later ones. A loop session works through them top to bottom.
- **Right-size the investigation.** Simple feature = a few agents. Complex migration = the full budget. Don't over-scout simple tasks or under-scout complex ones.
