#!/usr/bin/env bash
# Copy shared/onboarding.md into every skill's references/ directory.
# Skills are installed one directory at a time, so each needs its own copy.
# Run after editing shared/onboarding.md. `--check` exits non-zero if any copy is stale.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=shared/onboarding.md
status=0
for skill in skills/*; do
  dest="$skill/references/onboarding.md"
  if [ "${1:-}" = "--check" ]; then
    if ! cmp -s "$SRC" "$dest" 2>/dev/null; then
      echo "stale: $dest (run scripts/sync-shared.sh)"; status=1
    fi
  else
    mkdir -p "$skill/references"
    cp "$SRC" "$dest"
    echo "synced $dest"
  fi
done
exit $status
