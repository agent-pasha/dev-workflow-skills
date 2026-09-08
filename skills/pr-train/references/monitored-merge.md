# Monitored Sequential Merge — Operational Detail

Companion to [Workflow D](../SKILL.md#workflow-d--agent-driven-sequential-merge-monitored): how to actually drive a sequential train to completion — one PR at a time, monitored, optionally auto-merged. Examples use `<owner>/<repo>` as the slug; the reference poller defaults to the current repo via `gh repo view`. Always re-check the target repo's branch protection (below) rather than assuming values.

## Monitor mechanism

Use a **persistent** monitor, not a detached background shell. A `run_in_background` shell only notifies the agent when the process *exits*, so an unbounded poll loop's mid-watch event lines are never delivered — the watch is effectively silent until it ends. The `Monitor` tool with `persistent: true` is built for session-length PR watches: each stdout line becomes a chat notification, and it runs until the PR reaches a terminal state or the session ends.

Drive it off a compact **signature** so it notifies on change, not on every poll: emit an event only when an actionable signal moves, and exit on MERGED/CLOSED.

### Poll signature

Signature per poll: `state | mergeStateStatus | #reviews | #issueComments | #inlineComments | #failedChecks`.

- **Include `mergeStateStatus`.** On a repo with strict / up-to-date checks (`required_status_checks.strict: true`), a PR silently goes `BEHIND` whenever `main` moves — no other field changes, so without this the monitor never fires and automerge stalls forever. Treat `BEHIND` as an event → rebase + force-push.
- **Count by paginating ids, not `--jq length`.** `gh api <list> --jq length` counts only the first page (30 items), so a churny PR (a bot reviewer that posts a review object per push will do this) freezes that field and new activity stops registering. `--paginate` with `--jq '.[].id'` streams every page's ids; count them with `grep -c .`. (`--slurp` can't combine with `--jq`, so don't reach for it.) Extracting ids also means no comment body is ever materialized — sidestepping the control-character failures you can hit capturing body-bearing `gh pr view --json reviews,comments` output and re-parsing it with a separate `jq`.

```bash
sm=$(gh pr view "$PR" --repo "$REPO" --json state,mergeStateStatus --jq '.state+"|"+.mergeStateStatus')
nrev=$(gh api   --paginate "repos/$REPO/pulls/$PR/reviews?per_page=100"   --jq '.[].id' | grep -c .)
nissue=$(gh api --paginate "repos/$REPO/issues/$PR/comments?per_page=100" --jq '.[].id' | grep -c .)
ninline=$(gh api --paginate "repos/$REPO/pulls/$PR/comments?per_page=100" --jq '.[].id' | grep -c .)
failed=$(gh pr checks "$PR" --repo "$REPO" --json name,bucket --jq '[.[]|select(.bucket=="fail").name]|join(",")')
```

`gh pr checks --json` reads the machine-readable `bucket` (`pass`/`fail`/`pending`/`skipping`/`cancel`) — stabler than `awk`-parsing the human table on the literal `fail` token or tab spacing.

### Reference poller

```bash
#!/usr/bin/env bash
# Emits one line per actionable change; exits on MERGED/CLOSED. Run under a
# persistent monitor. Tolerates transient API blips (keeps the old baseline).
set -uo pipefail
PR="${1:?pr}"; INTERVAL="${2:-240}"
REPO="${3:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
# Count ids on a page-complete stream; return non-zero if the gh call failed,
# so a transient API error yields ERR instead of a bogus 0 (and a false EVENT).
count() { local out; out=$(gh api --paginate "$1" --jq '.[].id' 2>/dev/null) || return 1; printf '%s' "$out" | grep -c . || true; }
snapshot() {
  local sm nrev nissue ninline failed
  sm=$(gh pr view "$PR" --repo "$REPO" --json state,mergeStateStatus \
         --jq '.state+"|"+.mergeStateStatus' 2>/dev/null) || { echo "ERR"; return; }
  [ -z "$sm" ] && { echo "ERR"; return; }
  nrev=$(count "repos/$REPO/pulls/$PR/reviews?per_page=100")    || { echo "ERR"; return; }
  nissue=$(count "repos/$REPO/issues/$PR/comments?per_page=100") || { echo "ERR"; return; }
  ninline=$(count "repos/$REPO/pulls/$PR/comments?per_page=100") || { echo "ERR"; return; }
  # checks: non-zero exit just means failing/pending, not an API error — capture and parse.
  failed=$(gh pr checks "$PR" --repo "$REPO" --json name,bucket \
             --jq '[.[]|select(.bucket=="fail").name]|join(",")' 2>/dev/null)
  echo "${sm}|${nrev}|${nissue}|${ninline}|${failed}"
}
BASE=$(snapshot); echo "ARMED $PR [$BASE]"
while true; do
  sleep "$INTERVAL"; CUR=$(snapshot); ST=${CUR%%|*}
  [ "$ST" = "ERR" ] && continue
  [ "$CUR" != "$BASE" ] && { echo "EVENT $PR was=[$BASE] now=[$CUR]"; BASE="$CUR"; }
  case "$ST" in MERGED|CLOSED) echo "TERMINAL $PR $ST"; exit 0;; esac
done
```

**Expect self-echo.** Your own replies bump `#reviews` and `#inlineComments`, so an EVENT often fires for work you just did. When one lands, check the newest reviews'/comments' authors and timestamps before reacting — don't answer your own replies, and don't mistake a bot's withdrawal/acknowledgement for a new ask.

## Session-teardown recovery

A session can end (or the monitor be torn down) with **no completion marker** — the watch just stops. On the next turn, don't assume it's alive, and don't trust a baseline stashed in a scratch directory (it may have been wiped with the session). Reconcile against GitHub truth instead: compare the newest review/comment timestamps and the PR state to your own last action. Nothing postdates your last reply → nothing slipped through; re-arm. Something did (a new review, a failed check, or the PR already merged/closed) → handle it first, then re-arm or advance. Recreate the poller script if it's gone.

## Rebase recipe

When each branch is exactly one commit on top of its predecessor, its rebase anchor is its own parent, so the recipe is uniform:

```bash
git fetch origin main
git rebase --onto origin/main <branch>~1 <branch>   # replays only this branch's single commit onto main
<area gates>                                          # your repo's build/test/lint commands, scoped by risk tier
git push -f origin <branch>
```

If a branch is **not** one commit, `<branch>~1` drops everything below the tip — anchor on the predecessor's old tip (`--onto origin/main <prev-old-tip> <branch>`). Conflicts cluster in files shared across chunks (dependency wiring, routers, settings, sidebars, shared type / api-client modules) when main moves under the train — resolve preserving both sides' intent, and stop to ask if the resolution isn't obvious.

## Tool-version drift — confirm CI is actually red before "fixing"

A local formatter/linter can disagree with the version CI pins (e.g. a formatter pinned loosely as `>=X.Y` in the project config, so a newer local version reformats lines the CI version accepts). **Before applying a reformat your local tool flags, confirm CI's own check is failing** — `gh pr checks <#>`. Applying a local-only reformat can *break* a format check that was green. Fix what CI fails on, not what your local tool prefers; the same caution applies to any lint/format autofix the CI job doesn't reproduce.

## Automerge

```bash
gh pr merge <#> --auto --squash     # merges automatically once base-branch protection is satisfied
```

`--auto` waits for the base branch's required approvals **and** green checks — but it is only as safe as that protection, so verify before arming:

```bash
gh api repos/<owner>/<repo>/branches/<base>/protection \
  --jq '{req_approvals: .required_pull_request_reviews.required_approving_review_count,
         dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
         last_push_approval: .required_pull_request_reviews.require_last_push_approval,
         strict: .required_status_checks.strict,
         conversation: .required_conversation_resolution.enabled}'
```

- **No required approval → `--auto` merges on green CI alone**, i.e. unreviewed. Only enable it there for near-zero-risk paths, with the engineer explicitly aware.
- **Stale approvals.** If `dismiss_stale` and `last_push_approval` are both false (a common default), an approval survives later pushes — so an armed `--auto` will merge commits the approver never saw. Before pushing to a PR that already has its required approval, `gh pr merge <#> --disable-auto`, push, and re-arm only after the reviewer has re-seen the commits.
- **Repo + state constraints.** The repo must have auto-merge enabled (`allow_auto_merge: true`), and `--auto` errors on an already-mergeable PR (`Pull request is in clean status`) — for those, merge directly only when the engineer has the rights and no required approval is being skipped.

Match the merge method to repo convention (`--squash` is the common default). Never `--admin`-merge and never approve your own PR to satisfy the gate.

## Unresolved conversations block merge

Where the base enforces conversation resolution (`required_conversation_resolution`, or a ruleset's thread-resolution rule), an armed automerge sits green-and-approved but unmerged until every inline thread is resolved. After you address an inline comment and reply, resolve that thread:

```bash
# thread_id from: gh api graphql -f query='{repository(owner:"<o>",name:"<r>"){pullRequest(number:<#>){reviewThreads(first:100){nodes{id isResolved}}}}}'
gh api graphql -f query='mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}' -f t=<thread_id>
```

`reviewThreads(first:100)` returns only the first page — capped at 100 by the API. A PR with more than 100 threads can hide an unresolved blocker past the cap, so page with `pageInfo{ hasNextPage endCursor }` + `after:` until `hasNextPage` is false before treating the PR as fully resolved.

Resolve only threads you actually addressed; never resolve a human's thread just to unblock the merge.

## Replying to an inline review comment

```bash
gh api --method POST "repos/<owner>/<repo>/pulls/<#>/comments/<comment_id>/replies" -f body="…"
```

Reply on the thread *after* you push the fix (or the correction), so the reviewer sees the resolution in context. Keep it to what changed and why; cite the code when correcting a wrong comment.
