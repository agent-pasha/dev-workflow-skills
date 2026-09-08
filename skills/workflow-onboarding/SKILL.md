---
name: workflow-onboarding
description: |
  Set up or refresh `.agents/workflow-context.md` — the one file every dev-workflow skill (research-document, implementation-plan, create-ralph-prompt, pr-train) reads for this repo's conventions: areas, specs dir, ticket/branch/commit format, build/test gates, local verification, PR rules, risk tiers, agent CLI.
  Infers as much as possible from the repository, then asks the user only what's left.
  Run once right after installing the skills, or whenever conventions change.
  Triggers: "onboard", "run onboarding", "workflow onboarding", "refresh workflow context", "set up workflow context", "/workflow-onboarding"
---

# Workflow Onboarding

Creates or refreshes `.agents/workflow-context.md` at the git root. Every other skill in this collection runs this same procedure automatically on first use when the file is missing; invoking it directly lets you do it once, up front, for the whole repo — and re-run it when conventions change.

Follow [references/onboarding.md](references/onboarding.md) in full:

1. **Infer** every section from the repository first (manifests, CI config, git history, PR metadata, local-env files). Read-only, no questions yet.
2. **Ask** only what could not be inferred, in one batch, each question stating what you inferred and offering a default.
3. **Write** `.agents/workflow-context.md` from the template, keeping the section headings exact.

When invoked explicitly, onboard **all** sections, not just the ones one skill needs. When the file already exists, show a diff of what would change before overwriting — existing hand-edits win over fresh inference unless the user says otherwise.

Finish by summarizing what was written in five lines, and recommend committing the file so the whole team and every agent share one set of conventions.
