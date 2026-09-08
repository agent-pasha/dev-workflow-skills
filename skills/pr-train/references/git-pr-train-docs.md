# git-pr-train Documentation

Upstream (GitHub only): https://github.com/realyze/pr-train — `npm install -g git-pr-train`.
GitLab support exists in community forks; if you use one, follow its README for install and token setup. The notes below apply to both.

## Platform Setup

### GitHub Token
1. GitHub Settings > Personal access tokens > Fine-grained tokens
2. Permissions: `Contents: Read-only`, `Pull requests: Read and write`
3. Save to `${HOME}/.pr-train`

### GitLab Token (forks with GitLab support)
1. User Settings > Access Tokens
2. Create token with `api` scope
3. Save where the fork expects it (commonly `${HOME}/.pr-train-gitlab`)

Forks with multi-platform support auto-detect the platform from the git remote URL, or take `--platform github|gitlab`.

## Commands Reference

```bash
git pr-train -p                    # Merge branches sequentially and push
git pr-train -r -p -f              # Rebase branches and force-push
git pr-train --init                # Generate initial .pr-train.yml
git pr-train -p --create-prs       # Create/update PRs/MRs
git pr-train -p -c -d              # Create draft PRs/MRs
git pr-train -p -c -b <branch>     # Create PRs with custom base branch
git pr-train -p -c --platform gitlab  # Explicitly specify platform (forks only)
```

## Configuration (.pr-train.yml)

Keep this file gitignored — it is per-developer working state, not repo content.

```yaml
prs:
  main-branch-name: main
  draft-by-default: true
  print-urls: true

trains:
  Feature Name:
    - feature/ticket/branch-one
    - feature/ticket/branch-two
    - feature/ticket/combined:
        combined: true
```

## Workflow Patterns

### One-by-One Workflow
Merge branches individually as approved:
1. Merge LGTM'd branch to main
2. Merge main into next branch (or rebase)
3. Change PR/MR base to main
4. Delete merged branch from .pr-train.yml
5. Run `git pr-train` to sync remaining chain

### Combined Branch Workflow
For PRs that cannot merge independently - the combined branch points to same commit as last sub-branch but PR is based off main (full diff). Get LGTMs for all sub-branches, then merge combined branch.

## PR/MR Behavior

- Titles come from each branch's HEAD commit message
- Running with `-c` again updates only the Table of Contents
- Works with self-hosted GitLab instances (forks with GitLab support)
- Draft MRs add "Draft: " prefix to titles
