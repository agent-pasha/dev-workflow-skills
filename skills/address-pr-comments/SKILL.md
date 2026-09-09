---
name: address-pr-comments
description: >
  Triage and address review comments on a GitHub PR — human or bot (CodeRabbit, Copilot, etc.).
  Fetches every unresolved thread, evaluates each against the code, the project's specs,
  knowledge base, and conventions (valid fix / dismiss with a cited reason / needs clarification),
  implements the fixes, runs the repo's lint/format/type gates, commits, replies on each thread,
  resolves the threads it settled, and propagates changes up a PR stack when the branch is in one.
  Works interactively or unattended from a CI job that fires on new review comments.
  Triggers on: "address PR comments", "review comments on PR #X", "fix PR feedback",
  "handle coderabbit/copilot comments", or when given a PR URL with review comments to address.
---

# Address PR Comments

The goal is not to accept every review comment. It is to leave the PR in a state where every thread has been answered with a grounded verdict — fixed, dismissed for a stated reason, or turned into a precise question — so that when the bot reviewer returns zero new comments, a human can do one final inspection and request team review with the obvious wrinkles already gone.

## Before you start: workflow context

This skill reads repo conventions from `.agents/workflow-context.md` at the git root. If that file is missing, or any section listed below is missing or still `TODO`, run the onboarding procedure in [references/onboarding.md](references/onboarding.md) first: infer from the repo, ask only what's left, write the file, then continue here.

**Context it needs:** `Gates` (lint/format/typecheck per area) · `Tickets, Branches, Commits` (commit format) · `Pull Requests` (review bots, conversation-resolution rule, risk tiers) · `Specs & Docs` (specs directory, decisions and knowledge base) · `Autonomous Sessions` (the agent's GitHub login).

## Workflow

### 1. Fetch PR context

```bash
gh pr view <number> --json title,body,headRefName,baseRefName,author --repo <owner>/<repo>

# Inline review comments (the main signal)
gh api repos/<owner>/<repo>/pulls/<number>/comments --paginate \
  --jq '.[] | "---\nID: \(.id)\nAuthor: \(.user.login)\nPath: \(.path):\(.line // .original_line)\nIn-reply-to: \(.in_reply_to_id // "-")\nBody: \(.body)\n"'

# Review bodies and top-level comments (bot summaries, "changes requested" rationale)
gh api repos/<owner>/<repo>/pulls/<number>/reviews --paginate --jq '.[] | select(.body != "") | "---\n\(.user.login) [\(.state)]: \(.body)\n"'
gh api repos/<owner>/<repo>/issues/<number>/comments --paginate --jq '.[] | "---\n\(.user.login): \(.body)\n"'
```

Then get thread state, because only unresolved threads need work:

```bash
gh api graphql -f query='{repository(owner:"<owner>",name:"<repo>"){pullRequest(number:<number>){reviewThreads(first:100){pageInfo{hasNextPage endCursor} nodes{id isResolved isOutdated comments(first:50){nodes{databaseId author{login} body}}}}}}}'
```

Page with `after:` until `hasNextPage` is false. **Work only threads where `isResolved` is false and the last comment is not yours** (your login is in the context file). Everything else was handled in an earlier pass — never re-triage it, and never reply to your own reply.

### 2. Detect a PR stack or train

Check whether the head branch belongs to a stack: `gh stack checkout <number>` then `gh stack view --json` (exit 2 means no stack). Note the layers above it for step 9.

Legacy trains live in the gitignored `.pr-train.yml`; if the head branch is listed there, note the downstream branches and the combined branch.

If the PR is in a stack or a train, load the `pr-train` skill before triaging — it owns the chain conventions (branch order, layer ownership, sync rules) that step 4 needs to interpret comments correctly.

### 3. Check out the branch

```bash
gh pr checkout <number>
```

Do this in a dedicated worktree if the engineer may be using the main checkout.

### 4. Triage every thread — grounded, not obedient

Read the referenced code for each comment. Then check it against the sources that outrank a reviewer's first impression:

- **The spec or research doc for this work** (the context file's specs directory) — is the "bug" actually the specified behaviour?
- **Decision records and the knowledge base** (context file → `Decisions & knowledge base`) — was this trade-off already decided, and why?
- **Repo conventions** (`AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md`, the formatter and linter config) — a style suggestion that fights the formatter is noise.
- **The rest of the PR and, for a stack, the whole chain** — reviewers see one slice.
- **Existing tests** — a proposed guard may already be pinned as intentional.

Classify:

| Verdict | Action |
|---|---|
| **Valid** | Implement the fix. |
| **Valid, minor** | Implement — cheap and correct. |
| **Dismiss** | Incorrect, contradicts a spec/decision/convention, out of scope for this PR, or would harm the feature. Reply with the cited reason. |
| **Needs clarification** | The comment is plausible but the right fix depends on intent you can't establish. Ask — the user interactively, or the reviewer on the thread when unattended. |

Bot reviewers have a variable signal-to-noise ratio. Typical noise: style nits the formatter already governs; "consider adding validation" with no failing input; speculative concurrency or security concerns that ignore an existing guard elsewhere in the file; suggestions that duplicate a downstream PR; refactors beyond the PR's scope. Typical signal: off-by-one and null-path bugs, missing error handling on a new call, mismatched types, tests asserting the wrong thing, doc/code drift. Judge each comment on its merits — the same bot produces both.

**Dismissals must cite something**: a file:line, a spec section, a decision record, a convention, or a test. "Not needed" is not a verdict.

Present the triage table before implementing (interactive mode):

```
### Comment N — <short title> (path:line)
**Verdict: Valid.** <reasoning, with citations>
```

**For PRs in a stack or train, evaluate each comment against the *whole* chain, not just this PR.** What looks like a defect at this slice may be intentional scaffolding for a downstream PR. Verify before accepting or dismissing:

- *"Unused field / dead code / dead prop"* — grep the downstream branches to confirm it stays unused in the end state. `gh pr checkout` fetches only the PR branch, so first `git fetch origin`, then `git grep <symbol> origin/<downstream-branch>`. If a downstream PR consumes it, the right fix is usually to land it here as planned scaffolding, not delete it.
- *"This guard is redundant / always true"* — confirm it's still redundant after downstream PRs land.
- *"This component is missing X"* — check whether X arrives in a downstream PR; if so, document the staging in a code comment instead of duplicating it.
- *"Type allows Y but the code assumes !Y"* — verify whether downstream PRs tighten the type or the runtime contract.

State the chain-context check explicitly in the triage entry when it changes the verdict (e.g. *"Verdict: Valid. Confirmed downstream `feature/x/wire-y` does not consume this prop"*).

### 5. Implement fixes

- Read each file before editing.
- Targeted changes only — no surrounding refactors, no "while I'm here".
- After all fixes, run the quality gates for every area the PR touches, from the context file's `Gates` table (format, lint, typecheck, and the touched tests). Fix what they flag before proceeding. Confirm CI's own check is red before applying a reformat your local tool wants — tool-version drift can make a local-only reformat *break* a green check.

### 6. Commit and push

One new commit per triage pass — never amend commits a reviewer has already seen. Use the context file's commit format, e.g.:

```bash
git add <files>
git commit -m "[TICKET] Address PR review: <summary>"
git push
```

If the PR is a one-commit-per-branch train chunk, the `pr-train` skill's commit-shape rule applies instead (amend into the chunk's single commit, force-push with lease).

### 7. Reply on every thread you triaged

The replies endpoint requires the **PR number** in the path — `pulls/comments/<id>/replies` without it returns 404.

```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments/<id>/replies -f body="<what was done, or the cited reason for dismissing, or the precise question>"
```

Reply *after* pushing the fix so the reviewer sees the resolution in context. Keep replies to what changed and why; cite code or the spec when correcting a wrong comment. For a review-level or top-level comment with no thread, reply as an issue comment (`gh pr comment <number> --body …`).

### 8. Resolve the threads you settled

Where the base branch enforces conversation resolution (context file → `Pull Requests`), open threads block the merge. Resolve what you settled:

- **Bot threads**: resolve after replying, whether fixed or dismissed.
- **Human threads**: resolve when you implemented exactly what was asked. When you dismissed or asked a question, leave it open — that thread is the human's to close.

```bash
# thread ids come from the reviewThreads query in step 1
gh api graphql -f query='mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}' -f t=<thread_id>
```

Never resolve a thread just to unblock a merge.

### 9. Propagate up the stack

If the branch is in a stack (step 2), replay the layers above it and push every moved branch:

```bash
gh stack rebase --upstack
gh stack push
```

Exit 3 means a layer conflicted: resolve the files, `git add`, then `gh stack rebase --continue` (or `--abort` to restore the stack). The gh-stack skill, if you have one, covers the recovery paths.

If the branch is in a legacy `.pr-train.yml` train instead: `git pr-train -r -p -f`, and confirm all downstream branches rebased cleanly. Conflict recovery for that path: [references/legacy-train-conflicts.md](references/legacy-train-conflicts.md). If in neither, skip this step.

### 10. Report

Summarize: threads fixed / dismissed / questioned, gates run, commit SHA, what remains open and why. In interactive mode this is your message to the user; in unattended mode post it as one PR comment.

## Running unattended (CI-triggered)

This skill is built to run from a CI job that fires on new review activity (`pull_request_review`, `pull_request_review_comment`), so new comments get addressed without a human in the loop. Differences from interactive mode:

- **No triage table to approve.** Proceed on `Valid` and `Valid, minor`; dismiss with citations; for `Needs clarification`, reply on the thread with the specific question and leave it open. Do not guess at intent.
- **Idempotency is the step-1 filter.** Only unresolved threads whose last comment is not yours. A run that finds nothing to do exits quietly without commenting.
- **Loop guard.** Never reply to your own replies; never @-mention any bot that dispatches on mentions; if the triggering event's author is you or another automation, exit.
- **Scope guard.** Fix only what a comment asked for. Never force-push a branch you don't own the commit shape of, never change the PR's base, never resolve a human's dismissed or questioned thread, never touch anything on a mission-critical path (context file risk tiers) beyond the exact comment.
- **Stop conditions.** Stop and post a comment asking for a human if: a gate fails and the fix isn't in the diff a comment pointed at, a rebase conflicts, a comment requires a design decision, or the same thread has bounced more than twice between you and the reviewer.
- **Report** as a single PR comment (step 10), so the human's final inspection starts from a summary.

A typical loop: push → bot review → this skill fixes/dismisses/replies → bot re-review → zero new comments → human does the final read and requests team review.

## Reference

- `scripts/resolve_head_wins.py` — collapses `<<<<<<< HEAD … >>>>>>>` blocks to the HEAD side across files; use only after manually confirming HEAD-wins is right for every conflict in those files (see the legacy-train reference for when that holds).
