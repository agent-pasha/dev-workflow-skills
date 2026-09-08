---
name: research-document
description: |
  Create a research document to build shared understanding of how the system works before planning implementation.
  Scope adapts to the task: from a single service/feature investigation to a full cross-system comparison.
  Use when you need to understand current state before making changes.
  Triggers: "research [topic]", "investigate [system]", "document how [feature] works", "create research doc for [task]", "/research-document"
---

# Research Document Generator

Produce a markdown research document in the specs directory that captures the **current state** of relevant systems/features. Purely descriptive — no implementation plans, no fixes, no TODOs. The goal is a shared mental model before implementation planning begins.

## Before you start: workflow context

This skill reads repo conventions from `.agents/workflow-context.md` at the git root. If that file is missing, or any section listed below is missing or still `TODO`, run the onboarding procedure in [references/onboarding.md](references/onboarding.md) first: infer from the repo, ask only what's left, write the file, then continue here.

**Context it needs:** `Repository` (areas and paths) · `Specs & Docs` (specs directory, docs to read first) · `Autonomous Sessions` (subagent budget, reference implementations).

Below, `specs/` means the context file's specs directory.

## Workflow

### 1. Scope

Determine what needs investigating from the user's request. If ambiguous, ask clarifying questions (what's in scope, what's out of scope, is there a comparison target). If the context file lists a reference implementation and the topic touches it, ask whether the research should compare against it.

Break the scope into **independent investigation areas** — each one bounded, parallelizable, and specific enough to name the files/packages/systems involved. Scale the number of agents to the scope (a single-feature investigation might need 2-3; a full cross-system comparison might need 10), within the context file's subagent budget.

### 2. Parallel Research

Create `specs/research-findings/{topic-slug}/` and launch background subagents — one per area, each writing to a numbered findings file (`01-area-name.md`, `02-area-name.md`, etc.) inside the topic subfolder. The `{topic-slug}` is derived from the research document name (e.g., `billing-migration` for `billing-migration-research.md`). If `specs/research-findings/` already contains subfolders from previous research, create the new topic subfolder alongside them.

If your agent has no subagent support, run the areas sequentially with the same file layout.

Each subagent must:
- Research only — no implementation plans or fixes
- Reference specific source files and line numbers
- May spawn child subagents for deeper investigation (stay within the budget)
- Write findings as markdown with clear sections

Report progress to the user as agents complete.

### 3. Synthesize

Read all findings files from `specs/research-findings/{topic-slug}/` and write `specs/{topic}-research.md`. The synthesis should:
- Stand alone — readable without the detailed findings, but link to them for deep dives
- Be scannable — a reader gets the full picture from headings + executive summary + gap analysis
- Be specific — file paths and line numbers, not vague descriptions
- Include an executive summary, architecture overview, domain-specific sections, and a consolidated gap analysis (if applicable)
- Categorize gaps as: critical / important / intentionally excluded — ask the user to confirm classifications

## Principles

- **Document what IS, not what should be.** This is a snapshot of current state.
- **Reference source code.** Every claim should trace back to a file and line number. Always use paths relative to the project root (e.g., `services/api/src/main.py:42`), never absolute paths.
- **Distinguish intentional from accidental.** "Not ported because replaced by X" is different from "missing, needs attention." Ask questions to clarify if ambiguous.
- **Use comparison tables** when examining two systems side by side.
- **Adapt depth to scope.** A narrow investigation of one feature doesn't need 10 sections — keep it proportional.

## Examples

**Narrow** — "Research how session management works":
- Session creation/expiry flow (service + DB)
- Scheduled cleanup jobs
- Session usage in request middleware and auth checks

**Medium** — "Research end-to-end order processing":
- Order creation and CSV import
- Validation and third-party tokenization
- Fulfillment workflow and dispatch
- Result aggregation and completion tracking
- Order monitoring API endpoints

**Wide** — "Compare the legacy and new service implementations":
- Project structure (both sides)
- Messaging/queue usage vs workflow engine
- Domain models comparison
- API endpoints comparison
- Business logic comparison
- Test coverage comparison
- External integrations comparison
- Infrastructure and deployment
