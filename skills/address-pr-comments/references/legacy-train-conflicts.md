# Resolving conflicts during legacy `git pr-train` propagation

Companion to step 9 of [SKILL.md](../SKILL.md). Only relevant when the PR's branch lives in a `.pr-train.yml` train rather than a `gh stack`.

`git pr-train -r` runs `git rebase <upstream>` on each branch in turn. When an earlier branch in the train was edited (e.g. you removed a redundant guard), the plain rebase replays *every* upstream commit on top of the new parent — including ones that were already integrated. If your edit overlaps any of those re-applied commits, the rebase conflicts even though the downstream branch's actual end state is already correct.

The structurally correct fix is to replay only the commits unique to the failing branch using `git rebase --onto`. That avoids re-applying upstream commits at all, so the spurious conflict never arises. Reach for the regex helper only when `--onto` itself can't deduplicate a real overlapping edit.

**Step 0 — enable rerere** (memoizes resolutions across the run):

```bash
git config rerere.enabled true
```

**Step 1 — when a rebase fails, prefer `rebase --onto`:**

1. `git rebase --abort` to drop the failing rebase.
2. Identify the failing branch's *own* commits — the commits it added on top of its previous parent in the train. If each train branch is a single commit (the common convention), that's just the tip; use `<branch>~1` as the cut-off. For multi-commit branches, count with `git log --oneline <upstream>..<branch>` from before the train run, then use `<branch>~N`.
3. Replay just those commits onto the new parent:
   ```bash
   git checkout <branch>
   git rebase --onto <new-parent> <branch>~N <branch>
   ```
   `<new-parent>` is whatever the train just rebased successfully (the branch immediately above `<branch>` in `.pr-train.yml`); `N` is the number of commits unique to `<branch>`.
4. Re-run `git pr-train -r -p -f`. The previously failing branch is now aligned and the train continues.

**Step 2 — fallback for genuine overlapping edits:**

If `rebase --onto` itself conflicts, the failing branch's own commits really do overlap your edit on the upstream. Inspect the first conflict by hand. When the upstream's already-rebased state (`HEAD`) is the intended end state and the re-applied commit is an older version of the same lines (typical pattern: a placeholder became the real implementation in a later PR), and the same trivial pattern repeats across a file, run the helper shipped with this skill:

```bash
python3 <path-to-this-skill>/scripts/resolve_head_wins.py <conflicted-path> [<conflicted-path> ...]
```

Then `git add` the file(s) and `git rebase --continue`. Always resolve the first occurrence manually before reaching for the script — a "both added" file, or one with genuine evolution on both sides, needs a true union, not HEAD-wins.
