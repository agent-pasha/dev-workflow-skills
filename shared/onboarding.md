# Workflow Context Onboarding

Every skill in this collection reads its repo-specific conventions from one file: **`.agents/workflow-context.md`** at the repository root. This document is the procedure for creating or refreshing that file. It is the same in every skill that ships it.

## When to run

Run onboarding when **any** of these is true:

1. `.agents/workflow-context.md` does not exist at the git root (`git rev-parse --show-toplevel`).
2. It exists, but a section the current skill needs (listed in that skill's "Context it needs") is missing or still contains `TODO`.
3. The user asks for it explicitly: "onboard", "run onboarding", "refresh workflow context", or `/workflow-onboarding`.

Otherwise read the file and continue with the skill — do not re-ask what it already answers.

When only some sections are needed and missing, onboard **only those sections** and leave the rest untouched.

## Step 1 — Infer (read-only, no questions yet)

Do your best to fill every section from the repository before asking anything. Use subagents for the file sweeps if your agent supports them; otherwise run them sequentially. Sources, in priority order:

| Section | Where to look |
|---|---|
| **Repository** — kind, default branch, areas | Root listing; `git symbolic-ref refs/remotes/origin/HEAD`; workspace manifests (`pnpm-workspace.yaml`, `package.json` workspaces, `go.work`, `Cargo.toml` workspace, `pyproject.toml`, `settings.gradle`, `pom.xml` modules); `CODEOWNERS`; top-level directories that contain their own manifest |
| **Specs & docs** | Existing `specs/`, `docs/`, `design/`, `rfcs/`, `adr/` dirs; `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` |
| **Tickets, branches, commits** | `git log --format=%s -n 200` (bracketed / prefixed keys like `[PROJ-123]`, `PROJ-123:`, `feat(scope):`); `git branch -r` (naming pattern); PR titles via `gh pr list --limit 50 --json title,headRefName`; `.gitmessage`; commitlint / conventional-commits config |
| **Gates** — build/test/lint/typecheck per area | CI workflows (`.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`); `Makefile`, `justfile`, `Taskfile.yml`; `package.json` scripts; `pyproject.toml` / `tox.ini` / `noxfile.py`; `pre-commit` config; `Cargo.toml`; language-specific test dirs |
| **Local environment** | `docker-compose*.yml`, `Tiltfile`, `skaffold.yaml`, `devcontainer.json`, `Procfile`, `.env.example`, README "getting started" section |
| **Pull requests** | `gh repo view --json nameWithOwner,defaultBranchRef,mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed,pullRequestTemplates`; `gh api repos/<slug> --jq '{allow_auto_merge, delete_branch_on_merge}'`; `gh api repos/<slug>/branches/<default>/protection` (may 403 — that's fine, record "unknown"); `gh label list`; `.github/PULL_REQUEST_TEMPLATE.md`; presence of bot reviewers in recent PRs (`gh pr view <n> --json reviews`) — Copilot, CodeRabbit, etc.; `.github/CODEOWNERS` |
| **Risk tiers** | `CODEOWNERS` (required reviewers per path), paths containing `auth`, `payment`, `billing`, `migration`, `infra`, `terraform`, `.github`; paths named `experimental`, `sandbox`, `playground`, `skills` |
| **Autonomous sessions** | Which agent CLIs are installed (`command -v claude codex opencode cursor-agent`); existing `specs/*-prompt.md` files; README mentions of loops |
| **Reference implementations** | Directories named `legacy`, `old`, `v1`, `-java`, `-python` alongside a newer sibling; README migration notes |

Keep track of **where** each inferred value came from (a path or command) so you can cite it in a Step 2 question; in the written file, cite sources only for non-obvious values (Step 3).

Committed repo guidance (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`) outranks your harness's ambient defaults whenever they conflict — for example on commit trailers or merge method. Record the repo's rule.

Three rules for judging what you find:

- **Stale-but-present sources.** Repos accumulate superseded setup docs, old CI READMEs, and abandoned tool configs. When two sources disagree, prefer the one with the most recent commit (`git log -1 --format=%cs -- <path>`), and prefer what CI actually runs over what docs say. Record superseded sources on a `Stale, do not follow:` line in the relevant section so the next agent doesn't rediscover them.
- **Commands that exist vs commands that gate.** A test job that is `continue-on-error`, `allow_failure`, or not in the required status checks is advisory, not blocking. Mark advisory gates as such in the `Gates` table notes and name the blocking set on the `Blocking in CI:` line.
- **Granularity.** Cap the `Areas` table at about ten rows: one per deployable service or app, plus one row each for `db`, cloud infra, local infra, and tests. Fold everything else into an `other` row rather than listing every directory that carries a manifest.

Subagents are worth it for the CI-workflow sweep and for repos with more than about five areas; for everything else, direct `grep`/`sed`/`ls` is faster than delegation.

## Step 2 — Ask only what's left

Collect every field you could not infer with reasonable confidence and ask them **in one batch** (aim for at most 6 questions; if more remain, ask the ones the current skill needs and mark the rest `TODO`). For each question:

- State what you inferred and from where, then ask for confirmation or correction — "I see `[PROJ-123]` prefixes in the last 200 commits; is that the ticket key format?" beats "What is your ticket key format?"
- Offer a default the user can accept with one word.
- Accept "use defaults" / "looks right" as an answer to the whole batch.

Questions that commonly survive inference:

1. Which paths are **mission-critical** (always need a human approval) vs **near-zero risk**?
2. Preferred **merge method** and whether **auto-merge** is ever acceptable.
3. **How to verify** a change on a live/local environment for each change type (not just unit tests).
4. Whether **AI-attribution trailers** (`Co-Authored-By: …`, `Generated with …`) are wanted in commits.
5. Which **agent CLI** runs autonomous loops here, and the **subagent budget** the user is comfortable with.
6. Whether an older **reference implementation** exists that research/plans should compare against.

Do not ask about anything the current skill will not use.

**Conservative defaults when the user can't confirm.** Risk tiers: any production service, customer-facing app, infrastructure, migration, CI, or auth/payment/PII code is **mission-critical** until a human says otherwise; only paths explicitly marked no-review (experimental dirs, agent skills, docs) default to near-zero. Automerge: off. Merge method: whatever the repo settings allow, preferring squash. Never lower a tier because you couldn't find evidence for it.

## Step 3 — Write the file

Write `.agents/workflow-context.md` from the template below. Rules:

- Keep the section headings **exactly** as in the template — skills look them up by name.
- Fill every field; use `none` for a deliberate absence and `TODO` for unknowns the user chose to skip.
- Use paths relative to the repo root.
- Put a one-line `<!-- source: … -->` comment after inferred values that came from a non-obvious place.
- Keep it under ~150 lines for a single project, ~200 for a large monorepo. It is read at the start of every skill invocation, so terse tables beat prose.
- You may append one extra section, `## Unconfirmed`, listing inferences a human still needs to check. Skills ignore it; the next onboarding run should try to resolve it.

Then show the user a five-line summary of what was written and recommend committing the file so the team (and every agent) shares one set of conventions. If the repo has an `AGENTS.md` or `CLAUDE.md`, suggest adding the line: `Workflow conventions for agent skills live in .agents/workflow-context.md.`

## Template

```markdown
# Workflow Context

<!-- Generated by dev-workflow-skills onboarding on YYYY-MM-DD.
     Edit freely. Re-run with "refresh workflow context". -->

## Repository
- Kind: monorepo | single project
- Default branch: main
- Areas:
  | Area | Path | Stack | Notes |
  |---|---|---|---|
  | api | services/api | Python 3.12 / FastAPI | |
  | web | apps/web | TypeScript / Next.js | |

## Specs & Docs
- Specs directory: specs/
- Read first: README.md, docs/architecture.md

## Tickets, Branches, Commits
- Tracker: Linear | Jira | GitHub Issues | none
- Ticket key pattern: PROJ-123 | none
- Branch naming: feature/<ticket>/<slug>
- Commit format: `[PROJ-123] Imperative summary.`
- AI attribution trailers: omit | allowed

## Gates
  | Area | Build | Test | Lint / Format | Typecheck |
  |---|---|---|---|---|
  | api | — | `uv run pytest tests/unit` | `ruff check . && ruff format --check .` | `ty check src` |
  | web | `pnpm build` | `pnpm test` | `pnpm lint` | `pnpm typecheck` |
- Full suite: `make test`
- Blocking in CI: api unit tests, web build + typecheck (everything else is advisory)
- Known CI/local drift: none
- Stale, do not follow: none

## Local Environment
- Start: `docker compose up`
- URLs: api http://localhost:8080, web http://localhost:3000
- Verify by change type:
  | Change | How to verify |
  |---|---|
  | API endpoint | curl against localhost:8080, check status + body |
  | DB migration | migration job logs + `psql … -c "\d table"` |
  | UI | open localhost:3000, check console, screenshot light+dark |

## Pull Requests
- Host: GitHub | GitLab
- Slug: owner/repo
- Merge method: squash | merge | rebase
- Branch protection: approvals=1, strict checks=true, conversation resolution=true, auto-merge=enabled | unknown
- Scope labels: none | list
- Review bots: none | Copilot, CodeRabbit
- PR template: none | .github/PULL_REQUEST_TEMPLATE.md
- Risk tiers:
  | Tier | Paths | Review requirement |
  |---|---|---|
  | mission-critical | services/api, infra/, db/, .github/ | ≥1 human approval, always |
  | internal | tools/admin, scripts/ | review recommended |
  | near-zero | experimental/, .agents/skills | author's discretion |

## Autonomous Sessions
- Agent CLI: claude | codex | other
- Non-interactive run: `cat <prompt> | claude --dangerously-skip-permissions -p`
- Subagent budget: 5 (simple) / 20 (large investigation)
- Reference implementations: none | legacy/ (Java service being replaced by services/api)
```
