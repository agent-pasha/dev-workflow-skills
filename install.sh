#!/usr/bin/env bash
# dev-workflow-skills installer (no Node required).
#
#   curl -fsSL https://raw.githubusercontent.com/agent-pasha/dev-workflow-skills/main/install.sh | bash -s -- [options]
#
# Options:
#   --agent <claude|codex|agents|all>   Agent(s) to install for. Repeatable. Default: all
#   --scope <project|user>              Project (./) or user (~/) install. Default: project
#   --skills <a,b,c>                    Comma-separated subset. Default: every skill in the repo
#   --dest <dir>                        Explicit target directory (overrides --agent/--scope)
#   --ref <git-ref>                     Branch/tag to install from. Default: main
#   --copy                              Copy into each agent dir instead of symlinking to .agents/skills
#   --source <local-dir>                Install from a local checkout instead of downloading
#   -h, --help
#
# Layout produced (default, --agent all, --scope project):
#   .agents/skills/<skill>/             canonical copy
#   .claude/skills/<skill> -> ../../.agents/skills/<skill>
#   .codex/skills/<skill>  -> ../../.agents/skills/<skill>
set -euo pipefail

REPO="${DWS_REPO:-agent-pasha/dev-workflow-skills}"
REF="main"
SCOPE="project"
DEST=""
COPY=0
SOURCE=""
AGENTS=()
SKILLS=""

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --agent)  AGENTS+=("$2"); shift 2 ;;
    --scope)  SCOPE="$2"; shift 2 ;;
    --skills) SKILLS="$2"; shift 2 ;;
    --dest)   DEST="$2"; shift 2 ;;
    --ref)    REF="$2"; shift 2 ;;
    --copy)   COPY=1; shift ;;
    --source) SOURCE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
[ ${#AGENTS[@]} -eq 0 ] && AGENTS=(all)

case "$SCOPE" in
  project) ROOT="$(pwd)" ;;
  user)    ROOT="$HOME" ;;
  *) echo "--scope must be project or user" >&2; exit 2 ;;
esac

# --- fetch -------------------------------------------------------------------
if [ -n "$SOURCE" ]; then
  SRC="$SOURCE/skills"
else
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/dws.XXXXXX")"
  trap 'rm -rf "$TMP"' EXIT
  echo "Downloading $REPO@$REF ..."
  curl -fsSL "https://codeload.github.com/$REPO/tar.gz/$REF" | tar -xz -C "$TMP"
  SRC="$(find "$TMP" -maxdepth 1 -mindepth 1 -type d | head -1)/skills"
fi
[ -d "$SRC" ] || { echo "no skills/ directory found in source" >&2; exit 1; }

if [ -n "$SKILLS" ]; then
  IFS=',' read -r -a WANTED <<< "$SKILLS"
else
  WANTED=()
  for d in "$SRC"/*/; do WANTED+=("$(basename "$d")"); done
fi
for s in "${WANTED[@]}"; do
  [ -f "$SRC/$s/SKILL.md" ] || { echo "skill not found: $s" >&2; exit 1; }
done

# --- place -------------------------------------------------------------------
copy_skill() { # <skill> <target-skills-dir>
  mkdir -p "$2"; rm -rf "$2/$1"; cp -R "$SRC/$1" "$2/$1"; echo "  copied  $2/$1"
}
link_skill() { # <skill> <target-skills-dir> <canonical-skills-dir>
  mkdir -p "$2"; rm -rf "$2/$1"
  local rel
  rel="$(python3 -c 'import os,sys;print(os.path.relpath(sys.argv[1],sys.argv[2]))' "$3/$1" "$2" 2>/dev/null || echo "$3/$1")"
  ln -s "$rel" "$2/$1"; echo "  linked  $2/$1 -> $rel"
}

if [ -n "$DEST" ]; then
  for s in "${WANTED[@]}"; do copy_skill "$s" "$DEST"; done
  echo "Installed ${#WANTED[@]} skill(s) into $DEST"; exit 0
fi

want() { for a in "${AGENTS[@]}"; do [ "$a" = "$1" ] || [ "$a" = all ] && return 0; done; return 1; }

CANON="$ROOT/.agents/skills"
if [ "$COPY" = 1 ]; then
  for s in "${WANTED[@]}"; do
    want agents && copy_skill "$s" "$CANON"
    want claude && copy_skill "$s" "$ROOT/.claude/skills"
    want codex  && copy_skill "$s" "$ROOT/.codex/skills"
  done
else
  for s in "${WANTED[@]}"; do
    copy_skill "$s" "$CANON"
    want claude && link_skill "$s" "$ROOT/.claude/skills" "$CANON"
    want codex  && link_skill "$s" "$ROOT/.codex/skills" "$CANON"
  done
fi

echo
echo "Installed ${#WANTED[@]} skill(s) (${WANTED[*]}) for: ${AGENTS[*]} [$SCOPE]"
echo "Next: open your agent in the target repo and run the onboarding once —"
echo "      say \"run workflow onboarding\" (or /workflow-onboarding) — it writes .agents/workflow-context.md."
