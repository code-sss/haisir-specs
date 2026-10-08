#!/usr/bin/env bash
# sync-specs.sh — copy committed specs into the frontend/backend devcontainers and 3-way merge them back.
# Usage:
#   ./sync-specs.sh push [frontend|backend|all] [--force]   host HEAD -> container(s), default all
#   ./sync-specs.sh pull <frontend|backend> [--base <sha>]
#
# push: refuses if the synced paths are dirty, if the container has no .spec-sha, or if its synced paths
#       differ from both that pushed sha and the last pull (= edits not pulled yet); --force skips the
#       container checks and discards those edits. Then makes <container>:/workspaces/haisir-specs an exact
#       copy of the synced paths at HEAD (container files absent from HEAD are deleted) and writes the host
#       HEAD sha to .spec-sha there.
# pull: refuses if the synced paths are dirty; copies the container copy into
#       .claude/plans/sync-spec/<container>/, then per changed file runs
#       git merge-file (ours = host HEAD, base = .spec-sha or --base, theirs = container)
#       into <staging>/.merged/, then moves the results into the working tree only if every merge ran
#       (all or nothing). Binary files are never merged or overwritten. Never deletes files.
# Output (pull): first line `OK merged <n> clean <n> conflicts <n>` or `REFUSED <reason>`, then
#   MERGED <path> (-<n> lines) | CONFLICT <path> (<n>) | BINARY <path> | CONTAINER-ONLY <path> (copy in <staging>)
#   | HOST-DELETED <path> | CONTAINER-DELETED <path>
#   merged = written without conflicts (-<n> = lines deleted vs host HEAD), clean = no container change,
#   conflicts = left with markers, BINARY = differs on both host and container, reported only.
#   HOST-DELETED = deleted on host since the push but changed in the container; CONTAINER-DELETED = in the
#   pushed sha and on host but deleted in the container. Both reported only.

set -euo pipefail

PATHS=( target Implementation_planning vision/requirements .claude/references CLAUDE.md )
CONTAINER_BASE=/workspaces/haisir-specs

SELF=$(realpath "$0")
cd "$(dirname "$SELF")"
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

usage() { sed -n '3,5p' "$SELF" | sed 's/^# //'; exit 1; }
refuse() { echo "REFUSED $*"; exit 1; }
reach() { docker exec "$1" true >/dev/null || refuse "cannot reach container $1 (stopped or missing?)"; }

check_clean() {
  [[ -z "$(git status --porcelain -- "${PATHS[@]}")" ]] ||
    refuse "uncommitted changes under ${PATHS[*]} (commit or stash first)"
}

# Synced paths that exist in commit $1 (git archive fails on a pathspec with no match).
rev_paths() {
  local p
  for p in "${PATHS[@]}"; do git cat-file -e "$1:$p" 2>/dev/null && echo "$p"; done
}

# Copy the container's synced paths into the fresh dir $2. Call reach first: a path absent there is skipped.
fetch() {
  local c=$1 d=$2 p
  rm -rf "$d"; mkdir -p "$d"
  for p in "${PATHS[@]}"; do
    docker exec "$c" test -e "$CONTAINER_BASE/$p" || continue
    mkdir -p "$d/$(dirname "$p")"
    docker cp "$c:$CONTAINER_BASE/$p" "$d/$(dirname "$p")/" || refuse "docker cp $c:$CONTAINER_BASE/$p failed"
  done
}

# One sha256 line per synced file under dir $1 (staging extras like .merged/ and .base are outside PATHS).
manifest() { (cd "$1" && { find "${PATHS[@]}" -type f -print0 2>/dev/null || true; } | sort -z | xargs -0r sha256sum); }

push_to() {
  local c=$1 force=$2 sha base present now stage="$ROOT/.claude/plans/sync-spec/$1"
  sha=$(git rev-parse HEAD)
  reach "$c"
  if [[ $force != 1 ]]; then
    base=$(docker exec "$c" cat "$CONTAINER_BASE/.spec-sha" 2>/dev/null) ||
      refuse "no $CONTAINER_BASE/.spec-sha in $c, so unpulled edits can't be ruled out: pull $c --base <sha> first, or push --force to overwrite"
    git cat-file -e "$base^{commit}" 2>/dev/null || refuse "$c was pushed from $base, not a commit here (push --force to overwrite)"
    fetch "$c" "$TMP/$c"; now=$(manifest "$TMP/$c")
    mkdir -p "$TMP/$c.base"; mapfile -t present < <(rev_paths "$base")
    git archive "$base" -- "${present[@]}" | tar -x -C "$TMP/$c.base"
    # unchanged since the push, or exactly what the last pull (against this same push) saw
    [[ $now == "$(manifest "$TMP/$c.base")" ]] ||
      { [[ $(cat "$stage/.base" 2>/dev/null) == "$base" ]] && [[ $now == "$(manifest "$stage")" ]]; } ||
      refuse "$c has edits not pulled since push ${base:0:7}: run pull $c first (or push --force to discard them)"
  fi
  mapfile -t present < <(rev_paths HEAD)
  docker exec "$c" mkdir -p "$CONTAINER_BASE"
  docker exec "$c" rm -rf "${PATHS[@]/#/$CONTAINER_BASE/}"   # exact copy: drop files deleted or moved on host
  git archive HEAD -- "${present[@]}" | docker cp - "$c:$CONTAINER_BASE"
  echo "$sha" > "$TMP/spec-sha"
  docker cp "$TMP/spec-sha" "$c:$CONTAINER_BASE/.spec-sha"
  echo "OK pushed $c ${sha:0:7}"
}

pull_from() {
  local c=$1 base=$2 stage="$ROOT/.claude/plans/sync-spec/$1" p f rel rc out files
  local merged=0 clean=0 conflicts=0 lines=() pend=()
  reach "$c"
  if [[ -z "$base" ]]; then
    base=$(docker exec "$c" cat "$CONTAINER_BASE/.spec-sha" 2>/dev/null) ||
      refuse "no $CONTAINER_BASE/.spec-sha in $c (legacy push): rerun with --base <sha of the last push>"
  fi
  git cat-file -e "$base^{commit}" 2>/dev/null || refuse "base $base is not a commit in this repo"

  fetch "$c" "$stage"   # ponytail: staging is this script's own scratch dir

  out="$stage/.merged"
  mapfile -d '' -t files < <(find "$stage" -type f -print0 | sort -z)
  for f in "${files[@]}"; do
    rel=${f#"$stage"/}
    if [[ ! -e "$rel" ]]; then
      if git show "$base:$rel" > "$TMP/base" 2>/dev/null; then
        cmp -s "$f" "$TMP/base" || lines+=("HOST-DELETED $rel")   # untouched in the container: the host deletion stands
      else lines+=("CONTAINER-ONLY $rel (copy in ${stage#"$ROOT"/}/$rel)"); fi
      continue
    fi
    if cmp -s "$f" "$rel"; then clean=$((clean + 1)); continue; fi
    git show "$base:$rel" > "$TMP/base" 2>/dev/null || : > "$TMP/base"   # added on both sides: empty base
    if cmp -s "$f" "$TMP/base"; then clean=$((clean + 1)); continue; fi  # container unchanged, host ahead
    if [[ $(git diff --no-index --numstat -- "$rel" "$f" || true) == -* ]]; then lines+=("BINARY $rel"); continue; fi
    rc=0; mkdir -p "$out/$(dirname "$rel")"
    git merge-file -p -L host -L base -L "$c" "$rel" "$TMP/base" "$f" > "$out/$rel" || rc=$?
    (( rc < 0 || rc > 127 )) && refuse "git merge-file failed on $rel (working tree untouched)"
    pend+=("$rel")
    if (( rc == 0 )); then merged=$((merged + 1)); lines+=("MERGED $rel")
    else conflicts=$((conflicts + 1)); lines+=("CONFLICT $rel ($rc)"); fi
  done
  while IFS= read -r -d '' rel; do   # host is clean here, so ls-files = HEAD
    [[ ! -e "$stage/$rel" ]] && git cat-file -e "$base:$rel" 2>/dev/null && lines+=("CONTAINER-DELETED $rel")
  done < <(git ls-files -z -- "${PATHS[@]}")
  for rel in "${pend[@]}"; do cat "$out/$rel" > "$rel"; done   # every merge ran: now write the tree
  echo "$base" > "$stage/.base"   # lets push accept a container that matches this pull
  for p in "${!lines[@]}"; do
    [[ ${lines[$p]} == MERGED* ]] &&
      lines[p]+=" (-$(git diff --numstat -- "${lines[$p]#MERGED }" | cut -f2) lines)"
  done

  echo "OK merged $merged clean $clean conflicts $conflicts"
  (( ${#lines[@]} )) && printf '%s\n' "${lines[@]}"
  return 0
}

[[ $# -ge 1 ]] || usage
case "$1" in
  push)
    target=all force=0
    for a in "${@:2}"; do
      case $a in frontend|backend|all) target=$a ;; --force) force=1 ;; *) usage ;; esac
    done
    check_clean
    if [[ $target == all ]]; then push_to frontend "$force"; push_to backend "$force"
    else push_to "$target" "$force"; fi ;;
  pull)
    [[ "${2:-}" =~ ^(frontend|backend)$ ]] || { echo "pull needs exactly one of: frontend backend"; usage; }
    base=""
    if [[ "${3:-}" == --base ]]; then base=${4:?--base needs a sha}; elif [[ -n "${3:-}" ]]; then usage; fi
    check_clean
    pull_from "$2" "$base" ;;
  *) usage ;;
esac
