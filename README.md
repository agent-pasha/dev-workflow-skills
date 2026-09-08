# dev-workflow-skills

Agent skills for the loop that actually ships features: **research → plan → autonomous execution → small reviewable PRs**. They work with Claude Code, Codex, and any other agent that reads `SKILL.md` folders, and they adapt themselves to your repo through a one-time onboarding step.

| Skill | What it does |
|---|---|
| [`research-document`](skills/research-document/SKILL.md) | Fans out subagents to document how a system *currently* works, then synthesizes one research doc with file:line references and a gap analysis. |
| [`implementation-plan`](skills/implementation-plan/SKILL.md) | Turns a research doc (or a fresh codebase scout) into a phased todo list of atomic tasks, each with concrete verification steps. |
| [`create-ralph-prompt`](skills/create-ralph-prompt/SKILL.md) | Writes a self-contained session prompt (plus a tracker for ad-hoc goals) for a one-task-per-session autonomous loop, and gives you the loop command. |
| [`pr-train`](skills/pr-train/SKILL.md) | Splits a finished feature into <500-LOC PRs, writes high-signal descriptions, and can drive the whole train through review and merge one PR at a time — with guardrails. |
| [`workflow-onboarding`](skills/workflow-onboarding/SKILL.md) | Runs the onboarding step on demand: infers your repo's conventions, asks only what's left, writes `.agents/workflow-context.md`. |

```
research-document ──▶ implementation-plan ──▶ create-ralph-prompt ──▶ (loop runs) ──▶ pr-train
      specs/X-research.md      specs/X-todo.md        specs/X-prompt.md                  N small PRs
```

Each skill also stands alone. Use `pr-train` on any branch, `research-document` before any refactor.

## Install (one command)

The [`skills`](https://github.com/vercel-labs/skills) CLI installs into 70+ agents. Pick a scope:

```bash
# Project scope (this repo only) — installs for every agent it detects
npx skills add agent-pasha/dev-workflow-skills --all

# User scope (every project on this machine)
npx skills add agent-pasha/dev-workflow-skills --all -g

# Specific agents only
npx skills add agent-pasha/dev-workflow-skills --all -a claude-code -a codex

# One skill
npx skills add agent-pasha/dev-workflow-skills --skill pr-train

# Non-interactive (CI, dotfiles scripts)
npx skills add agent-pasha/dev-workflow-skills --all -g -y
```

Later: `npx skills update` pulls new versions, `npx skills list` shows what's installed.

### Without Node

```bash
# Project scope, Claude Code + Codex (canonical copy in .agents/skills, symlinked into .claude/skills and .codex/skills)
curl -fsSL https://raw.githubusercontent.com/agent-pasha/dev-workflow-skills/main/install.sh | bash

# User scope
curl -fsSL https://raw.githubusercontent.com/agent-pasha/dev-workflow-skills/main/install.sh | bash -s -- --scope user

# Only some skills, only Claude Code, copies instead of symlinks
curl -fsSL https://raw.githubusercontent.com/agent-pasha/dev-workflow-skills/main/install.sh | bash -s -- --skills pr-train,implementation-plan --agent claude --copy

# Any other agent: point at its skills directory
curl -fsSL https://raw.githubusercontent.com/agent-pasha/dev-workflow-skills/main/install.sh | bash -s -- --dest ~/.config/some-agent/skills
```

`install.sh --help` lists every option. Where a skill directory lands for each agent:

| Agent | Project scope | User scope |
|---|---|---|
| Claude Code | `.claude/skills/<skill>/` | `~/.claude/skills/<skill>/` |
| Codex | `.codex/skills/<skill>/` | `~/.codex/skills/<skill>/` |
| Agent-neutral (`AGENTS.md` ecosystem, Cursor, OpenCode, …) | `.agents/skills/<skill>/` | `~/.agents/skills/<skill>/` |

## Onboarding: making the skills fit your repo

These skills were distilled from one team's workflow, and most of their value comes from being tailored: real test commands, real branch protection, real risk tiers. Rather than ship those baked in, every skill reads them from one file at your repo root:

```
.agents/workflow-context.md
```

**The first time any skill runs in a repo without that file, it onboards itself:**

1. **Infers** as much as it can from the repository — workspace manifests, CI workflows, `Makefile`/`package.json` scripts, `git log` ticket prefixes, branch names, PR templates, labels, branch protection, `docker-compose`/`Tiltfile`, `CODEOWNERS`, existing docs.
2. **Asks you only what it couldn't infer**, in one batch, each question showing what it found and offering a default. Typical survivors: which paths are mission-critical, whether auto-merge is ever OK, how to verify a change on a live environment, whether AI-attribution trailers are wanted.
3. **Writes the file** and asks you to commit it, so every teammate and every agent shares the same conventions.

To do it up front instead of on first use, run the onboarding right after installing:

```
/workflow-onboarding          # Claude Code
"run workflow onboarding"     # any agent
```

Re-run it whenever conventions change ("refresh workflow context"). The file is plain markdown — edit it by hand any time. The full procedure and the file template live in [`shared/onboarding.md`](shared/onboarding.md).

What the file captures:

| Section | Used by |
|---|---|
| Repository — monorepo areas and paths | research-document, implementation-plan |
| Specs & Docs — where research/plans/prompts go | all |
| Tickets, Branches, Commits — key format, naming, trailers | pr-train, create-ralph-prompt |
| Gates — build/test/lint/typecheck per area | pr-train, implementation-plan, create-ralph-prompt |
| Local Environment — start command, how to verify each change type | implementation-plan, create-ralph-prompt, pr-train |
| Pull Requests — merge method, protection, labels, bots, risk tiers | pr-train |
| Autonomous Sessions — agent CLI, loop command, subagent budget, reference implementations | research-document, implementation-plan, create-ralph-prompt |

## Philosophy

- **Research before planning, plan before executing.** Every plan task points at real files and ends with a verification step. "It should work" is not verification.
- **One task per session.** Autonomous loops restart with a fresh context for each task, so progress is incremental and reversible.
- **Small PRs, paced.** Under 500 lines of meaningful diff, reviewable cold, one open at a time. A feature that needs 30 PRs gets 30 PRs — over time, not all at once.
- **Guardrails over trust.** The agent never approves its own PR, never admin-merges, never force-pushes anything but the chunk's own branch, and stops to ask on anything destructive or ambiguous.
- **Conventions live in the repo, not in the skill.** The onboarding file is the contract between the skills and your team.

## Requirements

- An agent that supports `SKILL.md` skills (Claude Code, Codex, Cursor, OpenCode, …).
- `git`, and for `pr-train`: the [GitHub CLI](https://cli.github.com/) (`gh`), optionally with `gh extension install github/gh-stack` for stacked PRs.
- Subagent support in your agent makes `research-document` and `implementation-plan` much faster, but both fall back to sequential investigation.

## Contributing

- `shared/onboarding.md` is the single source for the onboarding procedure. After editing it, run `scripts/sync-shared.sh` to copy it into each skill's `references/`; CI fails if the copies drift.
- Keep skills repo-agnostic. Anything team-specific belongs in `.agents/workflow-context.md`, which the skills read at runtime.
- Test a change by installing from your checkout: `./install.sh --source . --dest /tmp/skills-test`.

## License

MIT — see [LICENSE](LICENSE).
