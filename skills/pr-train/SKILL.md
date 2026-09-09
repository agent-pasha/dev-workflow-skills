---
name: pr-train
description: |
  Split large features into small, individually-reviewable PRs and pace them through review.
  Default workflow: sequential individual PRs (one PR open at a time, paced through review/merge).
  Fallback: a GitHub PR stack driven with `gh stack` for chains that can't be merged independently.
  Legacy: `git pr-train` for GitLab or for trains that already live in `.pr-train.yml`.
  Use when:
  (1) Planning how to split implemented changes into PRs
  (2) Creating the first/next PR in a sequence for a ticket
  (3) Writing a high-signal PR description (intent, screenshots, how-tested)
  (4) Deciding between sequential individual PRs vs a `gh stack` chain vs a combined branch
  (5) Creating, syncing, or merging a PR stack for a chain of dependent PRs
  (6) Fixing failing tests in stack branches
  (7) Driving a sequential train to completion under agent monitoring — one PR open at a time, watched, feedback addressed, merged (optionally auto-merged), then the next opened
  Triggers: "split into PRs", "create pr train", "pr-train", "pr stack", "stack these PRs", "next PR for", "update pr train", "fix branch tests", "submit pr train", "drive the train", "monitor and merge the train", "automerge the train", "watch this PR and open the next"
---

# Splitting Features Into Reviewable PRs

This skill operationalizes one rule: every PR that lands on the default branch must be small, reviewable cold, and paced — even when the feature behind it was built end-to-end in one go.

## Before you start: workflow context

This skill reads repo conventions from `.agents/workflow-context.md` at the git root. If that file is missing, or any section listed below is missing or still `TODO`, run the onboarding procedure in [references/onboarding.md](references/onboarding.md) first: infer from the repo, ask only what's left, write the file, then continue here.

**Context it needs:** `Tickets, Branches, Commits` · `Gates` · `Pull Requests` (including risk tiers) · `Autonomous Sessions` (agent CLI, for Workflow D).

Wherever this skill says *ticket key*, *area gates*, *scope labels*, *risk tier*, *merge method*, or *repo slug*, the value comes from that file.

## Core Principle

> Huge PR trains are an antipattern.

Even when AI delivers a feature end-to-end, that output is a POC. Each PR going into `main` must be:

- **Small enough to review in under 30 minutes in one go** — aim for **< 500 LOC of meaningful diff** (excluding lockfiles, snapshots, generated code, bulk renames).
- **Reviewable cold** — a reviewer should not need to read prior or future PRs to understand this one.
- **Independently mergeable when possible** — if it must depend on an unmerged PR, the description must explain how to review it standalone, or it should wait until the prior PR has merged.
- **Self-reviewed first** — open it, read your own diff, fix what you'd flag, _then_ request review.

If a feature genuinely needs 30–50 PRs, that's fine. Pace them. Don't drop a wall of open PRs on the team.

## Pick the Workflow

| Approach | When to use | Trade-off |
|---|---|---|
| **Sequential individual PRs** (default) | Each chunk can be merged on its own. The most common case. | Slower wall-clock — you wait for review/merge before opening the next. |
| **PR stack** (`gh stack`) | Chunks build on each other but each still passes CI standalone. | Reviewer sees a chain; each PR still needs to be reviewable cold. |
| **Combined branch** | Chunks genuinely can't compile/test independently (rare — push back on this first). | Reviewers approve sub-PRs, then the whole stack merges in one shot. |

Default to **sequential individual PRs**. Only reach for a stack when sequencing would force you to keep stale unmerged work for days.

These three choose how to **split** a train. To **drive** a sequential train to completion under agent supervision — one PR open at a time, monitored, feedback addressed, optionally auto-merged — layer [Workflow D](#workflow-d--agent-driven-sequential-merge-monitored) on top of A or B.

## Workflow A — Sequential Individual PRs (Default)

1. **Plan the split** from the working POC. Group changes into chunks that:
   - Each compile + test independently.
   - Each makes sense to a reviewer with no prior context.
   - Each target **< 500 LOC** of meaningful diff.
   - Respect [code review boundaries](#code-review-boundaries) — keep mission-critical code separate from low-risk tooling/script changes so reviewers focus on what matters.
2. **Stash or branch off the rest.** Cut `feature/<ticket>/<chunk-1>` (or whatever the context file's branch naming says) from `main` with only chunk 1's changes.
3. **Self-review the chunk's diff.** `git diff main...HEAD` — would you approve this? Fix anything you'd comment on.
4. **Open the PR** with a [compliant description](#pr-description-requirements) and the repo's scope labels, if it uses them. Mark draft if local QA isn't done; mark `Ready to review` once it is.
5. **Address review comments** with the `address-pr-comments` skill — whatever the count.
6. **Request review, get approval, merge.**
7. **Rebase your remaining work onto updated `main`** and repeat for chunk 2.

This pacing is deliberate. It keeps the PR queue manageable and gives _you_ time to read each chunk before defending it.

**Offer to drive it.** Once the chunks are cut and ready to push, offer the engineer the monitored-merge automation ([Workflow D](#workflow-d--agent-driven-sequential-merge-monitored)) — open one PR, watch it, address feedback, merge (optionally auto), then open the next — instead of shepherding each PR by hand.

## Workflow B — PR Stack (`gh stack`)

Use only when chunk N+1 genuinely needs code from chunk N to compile or test, but each branch can still pass CI on its own merged state.

The chain is a GitHub **stack** ([stacked pull requests quickstart](https://docs.github.com/en/pull-requests/get-started/stacked-prs-quickstart)): every branch has one PR based on the branch below it, GitHub shows reviewers only that layer's diff, and after a bottom PR squash-merges the layers above are retargeted and rebased for you. The `gh stack` CLI drives it — see `gh stack --help` (or a dedicated gh-stack skill, if you have one) for command details, non-interactive flags, exit codes, and conflict recovery. This section covers only what this skill adds on top.

1. **Set up once:** `gh extension install github/gh-stack` and `git config rerere.enabled true`.
2. **Build the stack bottom-up** while cutting chunks — `gh stack init <chunk-1-branch>`, commit, `gh stack add <chunk-2-branch>`, commit, and so on. Branch names follow [Branch Naming](#branch-naming). Put foundational work at the bottom.
3. **Push and open drafts:** `gh stack submit --auto`. Titles and bodies are auto-generated, so rewrite each with `gh pr edit` to a [compliant description](#pr-description-requirements) and apply scope labels.
4. Each PR description **must** explain how to review it standalone — what assumptions hold from prior PRs, what to focus on in this diff. Leave stack navigation out of the body: the GitHub stack UI carries it.
5. **Review fixes land on the layer that owns them** (`gh stack checkout <branch>`, commit, `gh stack rebase --upstack`, `gh stack push`). Multiple commits per layer are fine; never amend commits a reviewer has already seen.
6. **Merge from the bottom up.** After each squash-merge, `gh stack sync` (`--prune` to drop merged local branches). Use `gh stack merge <pr> --yes --squash` to land a PR plus everything below it; never `gh pr merge` on a stack.
7. **Branches already pushed with plain PRs** (or by another tool) join a stack without any rewrite: `gh stack link <pr-bottom> … <pr-top>`, then `gh stack checkout <stack-number>` for local tracking.

Always run the non-interactive forms — `gh stack view --json`, `submit --auto`, `merge … --yes` — because the bare commands open a TUI and block an agent session.

## Workflow C — Combined Branch

When sub-branches can't be tested independently. Sub-branches get LGTMs, then the whole set merges in one shot.

With a stack this is just `gh stack merge <top-pr> --yes --squash`: all-or-nothing, bottom-up, no extra branch. A separate combined branch (see [Legacy: git pr-train](#legacy-git-pr-train)) is only for GitLab or a pre-existing `.pr-train.yml` train.

Before choosing this: try harder to make branches independent (feature flags, stub interfaces, parallel implementations behind a toggle). Combined merges lose most of the reviewability benefit of splitting.

## Workflow D — Agent-Driven Sequential Merge (Monitored)

Not a fourth way to *split* a train — an automation layer that *drives* a sequential train (Workflow A, or a stack from B) to completion: **one PR open at a time**, an agent monitoring each PR, acting on its review/CI events, then opening the next after it merges. Reached via the offer in [Workflow A](#workflow-a--sequential-individual-prs-default), or on direct request ("drive the train", "monitor and merge").

### Get consent before driving

Confirm three things up front:

1. **Per-chunk QA done?** "Branches cut and ready to push" is not "QA'd." Any chunk whose local QA (the context file's `Local Environment` → verify-by-change-type table) isn't finished opens as a **draft** with automerge off until it is.
2. **Automerge — on or off?** (default **off**)
   - **Off** — the agent opens each PR, monitors it, and addresses feedback, then hands the merge to the team. It advances to the next chunk only after the team merges.
   - **On** — the agent enables GitHub native auto-merge (`gh pr merge <#> --auto --squash`); the PR merges once its base-branch protection is satisfied. **Automerge is only as safe as that protection — first verify it** (`gh api repos/<owner>/<repo>/branches/<base>/protection`). Enable it only where protection enforces the review this train's [risk tier](#code-review-boundaries) needs. If the base requires no approval, `--auto` merges on green CI alone — i.e. **code no human reviewed**; acceptable only for near-zero-risk paths, and only with the engineer explicitly told that's what will happen. Never arm it on a mission-critical train whose base doesn't enforce an approval.
3. **Merge method** — confirm it matches the context file (squash is the common default).

Never approve your own PR, never admin-merge, never bypass branch protection.

### The loop (per chunk)

1. **Rebase onto latest main + gate.** For a stack, `gh stack sync` does the rebase and retargeting. For loose sequential branches, confirm the chunk is a single commit on its predecessor (`git rev-list --count <prev>..<branch>` = 1) before `git rebase --onto origin/main <branch>~1 <branch>`; for a multi-commit chunk, anchor on the predecessor's old tip instead (`git rebase --onto origin/main <prev-old-tip> <branch>`) or the tip commits are dropped. Run the chunk's area gates (context file → `Gates`, scoped by [risk tier](#code-review-boundaries)), then push (`gh stack push` for a stack, force-push with lease otherwise). Do all of this in a **dedicated worktree**, never the engineer's main checkout.
2. **Open the PR** — compliant [description](#pr-description-requirements), scope labels. Draft only if this chunk's QA isn't done (consent Q1).
3. **Arm a persistent monitor** on the PR — poll ~4 min for new reviews, new issue comments, new inline review comments (author + text), CI check failures, and **merge-state changes (including `BEHIND`)**. Emit one event per change; exit on MERGED/CLOSED.
4. **Handle each event** ([playbook](#event-handling) below).
5. **Arm automerge only when the chunk is settled** (opted in, QA done, no fix-push you're still expecting). A stale approval is **not** re-requested on push unless the base enforces it (`dismiss_stale_reviews_on_push` / `require_last_push_approval`) — so if you must push to a PR that already carries its required approval, `gh pr merge <#> --disable-auto` first and re-arm only after the reviewer has seen the new commits.
6. **On MERGED** → `git fetch origin main`, rebase the next chunk (step 1), repeat. **On CLOSED-without-merge** → stop and ask the engineer.
7. **After the last chunk merges** → summarize what merged; remind that **merged ≠ deployed** where deploys are manual.

Silence is not progress. If a PR stalls — CI never greens, a required approval never lands, or it sits `BEHIND` — the signature stops changing and the monitor goes quiet; if a PR hasn't moved in a while, tell the engineer what it's waiting on.

### Event handling

**Review comments → triage every one, whatever the count.** Whenever review comments land — inline or top-level, bot or human, one or many — run the triage flow: classify each comment (valid fix / dismiss with a stated reason / needs clarification), implement the fixes, run the lint/format/type gates, reply on each thread, and propagate the change up the stack. Invoke the `address-pr-comments` skill from this collection rather than re-deriving that flow inline. Don't wait for a batch — it's the comment path for a single comment too. The rest of the event space — CI, merge-state, conflicts — you handle directly:

| Event | Response |
|---|---|
| Review comment(s) — bot or human, any count | Run the triage flow; then **resolve each thread you addressed**. |
| A **human** disagrees / requests changes | The human decides — state your case with evidence if you disagree, then do what they land on. Authoritative over any bot and over your own read. |
| CI check fails | Diagnose, fix on the branch, re-run area gates locally, push. |
| PR goes `BEHIND` main | Rebase onto latest main and push (loop step 1) — required where the base uses strict / up-to-date checks. |
| Rebase conflict | Resolve preserving both sides' intent; if ambiguous, **stop and ask**. `gh stack sync` restores every branch on conflict; rerun `gh stack rebase` to resolve in place. |

Where the base enforces conversation resolution, merge blocks on open threads — so **resolve each inline thread you actually addressed** after replying. Never resolve a human's thread just to unblock the merge; that's theirs.

### Guardrails

- **One PR open at a time.** Never fan the whole train out at once.
- **Dedicated worktree** for every git operation — the engineer may be using their main checkout in parallel. `gh stack` local state lives in the shared git dir, so a stack checked out in one worktree is visible from the others.
- **Pin SHAs.** Branches can move under concurrent sessions; verify a branch tip before you rebase or force-push, and stop if it moved unexpectedly.
- **Preserve the branch's commit shape** on loose sequential branches — one-commit-per-branch chunks amend review fixes into that commit, otherwise the `<branch>~1` anchor drifts (loop step 1). A stack has no such constraint: `gh stack` tracks each layer's base itself.
- **The consent gate is a standing authorization, not a blanket one.** It authorizes exactly the agreed routine: rebasing and force-pushing each chunk's *own feature branch* (never `main`), and — if opted in — arming automerge per the loop's settle rule. Anything outside that routine gets a fresh yes/no: a force-push to anything but the chunk's feature branch, arming automerge on a base whose protection you haven't verified, or re-arming after a post-approval push. Don't re-ask before every routine feature-branch force-push, though — that just trains the operator to rubber-stamp.
- **Stop and ask** on anything destructive or ambiguous: a human closing a PR, a rejected force-push, rewritten `main` history, an unclear conflict.

Operational detail — the poll-signature monitor (mind pagination and the counts-not-bodies rule), tool-version drift, conversation resolution, session-teardown recovery, and the automerge commands: [references/monitored-merge.md](references/monitored-merge.md).

## Branch Naming

Use the pattern from the context file. The default this skill assumes when none is recorded:

```
feature/<ticket>/<short-description>
bugfix/<ticket>/<short-description>
hotfix/<ticket-if-exists>/<short-description>
```

Examples: `feature/PROJ-815/order-dtos`, `bugfix/PROJ-441/profile-access`, `hotfix/null-pointer-on-date-parse`.

## Commit Message Format

Use the format from the context file. Default:

```
[TICKET] Short description in a sentence.

More detailed, yet concise, explanation when necessary to give context/describe the changes.
```

- Prefix with the ticket key so the tracker auto-links the commit.
- AI-attribution trailers (`Co-Authored-By: …`, `Generated with …`): follow the context file. This skill's default is to **omit** them.

## PR Description Requirements

Most trackers (Linear, Jira, GitHub Issues) auto-link the ticket when its key appears in the PR title or description. If the repo has a PR template (context file → `PR template`), fill it — but apply the same signal rules below to every section.

Every PR description must answer:

1. **Intent / purpose** — what this PR accomplishes and why. One short paragraph.
2. **If part of a chain** — how this PR can be reviewed without reading prior/future PRs. What assumptions from prior PRs hold here. What's deliberately out of scope.
3. **How it was tested** — concrete. Examples:
   - `Confirmed in the local dev environment that the new API endpoints work, outputs are correct, and proper status codes are returned on errors.`
   - `Confirmed in the local dev environment that the new admin-only resource triggers a redirect when accessed with non-admin credentials.`
   - `Unit tests added in tests/unit/test_xxx.py; ran the full unit suite.`
4. **UI changes** — screenshots, and for each:
   - Light + Dark mode
   - Edge cases: loading, empty, error, long lists, very long words (overflow)
   - Customer-facing UI: mobile view (responsive check)
5. **Feature flag** — name the flag (if used) and its default. New production code should be flag-guarded where feasible so it can be turned off without rolling back.

Mark as `Draft` until local QA is done. Then `Ready to review`.

### Keep it high-signal

Every line of the description should help a reviewer either (a) know what to look at, (b) know what to verify, or (c) know what's intentionally out of scope. If a line does none of those, cut it.

**Omit:**

- **Empty placeholder sections.** If "Feature flag" or "UI changes" doesn't apply, drop the heading rather than writing `None` / `N/A`. Absent ≠ unaddressed.
- **Cross-PR navigation as body content.** The ticket tag and the stack UI already tell a reader where this PR sits. Don't list "what was split out" or "next branch is X" inside the description — that's author-context, not reviewer-context.
- **Implementation/split history.** "Previously bundled, now split because…" belongs in the closed-PR comment, not in the new PR's body.
- **Restating the diff.** "Adds a hook called X" reads from the file list. Write what is *not* obvious from looking at the diff: invariants, why the boundary lives where it does, what a reviewer should focus on.
- **Boilerplate chain framing.** "PR 3 of 14" / "independently mergeable" / "preceding chunks merged" — the stack + ticket already carry that.

**Keep:**

- One short paragraph of intent (the *why*, not a paraphrase of the file list).
- File-level pointers only when they call out a non-obvious responsibility, an invariant, or a boundary worth defending in review.
- The concrete `How tested` line(s).
- Anything a reviewer must assume from a still-unmerged prior PR — only when it's truly required to review this one cold.

A four-line description with only what reviewers need beats a twelve-line one padded with template scaffolding.

## Self-Review Gate

Before clicking `Request review`:

1. `git diff main...HEAD` — read it like a reviewer who's never seen this work.
2. Address every bot-reviewer comment (Copilot, CodeRabbit, etc.) you'd accept — or note why you're dismissing it.
3. Confirm the PR matches everything in [PR Description Requirements](#pr-description-requirements).
4. Re-check LOC: if it's drifting > 500, can a chunk peel off into a follow-up?

## Code Review Boundaries

When splitting, keep mission-critical code separate from low-risk changes so reviewers focus on what matters. The authoritative tier → path mapping is the context file's `Risk tiers` table; this is the shape it follows:

| Risk | Typical paths | Review requirement |
|---|---|---|
| **Mission-critical** | Production services, infrastructure-as-code, DB migrations, customer-facing apps, CI workflows (`.github`), anything touching auth / PII / billing | Full review + ≥1 approval, always. |
| **Internal operations** | Internal admin tools (logic/metrics), local dev-cluster manifests, ops scripts | Reviews recommended. Engineer-only admin UI: screenshots/GIFs suffice. |
| **Near-zero risk** | Personal experimental directories, agent skills / prompts (developer-productivity only), POCs/MVPs/demos | Reviews at engineer's discretion. |

Mixing an agent-skill tweak into the same PR as a production-service change wastes reviewer cycles. Split them.

## Typical Split Patterns

Use as a starting point, not a recipe. Each item is one PR (< 500 LOC):

**Backend feature**
1. DB schema (migration + changelog)
2. Entities + repos
3. DTOs / models
4. Service layer + unit tests
5. API controller / endpoint + tests

**Full-stack feature**
1. Backend foundation (schema, entities, repos)
2. Backend logic (services, DTOs)
3. Backend API (controllers, endpoint tests)
4. Frontend types / API client
5. Frontend components / UI
6. Polish (a11y, edge cases, copy)

If any of these chunks blow past 500 LOC, split further (e.g., "service layer" → "service core" + "service edge cases").

## Fixing Failing Tests on a Stack Branch

1. `gh stack checkout feature/<ticket>/<branch>` — the layer that owns the failure, not the top.
2. Diagnose and fix.
3. Commit.
4. `gh stack rebase --upstack` to replay the layers above, then `gh stack push`.

## Legacy: `git pr-train`

`git pr-train` predates GitHub stacks. Keep using it only for GitLab repos (via a fork with GitLab support) or for a train that already lives in `.pr-train.yml`; don't start new trains with it, and never run it on branches that are in a `gh stack` — the two fight over branch bases.

Keep `.pr-train.yml` **gitignored** — never `git add -f` it. CLI details, the yml format, the combined-branch pattern, and the one-by-one merge procedure: [references/git-pr-train-docs.md](references/git-pr-train-docs.md).

To move an existing train onto a stack: `gh stack link <bottom-pr> … <top-pr>`, `gh stack checkout <stack-number>`, delete the train from `.pr-train.yml`, and strip the `<pr-train-toc>` block from each PR body.
