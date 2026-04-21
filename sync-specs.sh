#!/usr/bin/env bash
# sync-specs.sh — copy specs dirs between local and containers
# Usage:
#   ./sync-specs.sh push [frontend|backend|all]   — local → container(s)
#   ./sync-specs.sh pull [frontend|backend]        — container → local

set -euo pipefail

DIRS=( target Implementation_planning )
FILES=( CLAUDE.md )
CONTAINERS=( frontend backend )
CONTAINER_BASE="/workspaces/haisir-specs"

usage() {
  echo "Usage:"
  echo "  $0 push [frontend|backend|all]   — local → container(s)"
  echo "  $0 pull [frontend|backend]        — container → local"
  echo ""
  echo "Examples:"
  echo "  $0 push              # push all dirs to both containers"
  echo "  $0 push frontend     # push all dirs to frontend only"
  echo "  $0 push backend      # push all dirs to backend only"
  echo "  $0 pull frontend     # pull all dirs from frontend"
  echo "  $0 pull backend      # pull all dirs from backend"
  echo ""
  echo "Dirs synced: ${DIRS[*]}"
  echo "Files synced: ${FILES[*]}"
  exit 1
}

push_to() {
  local container="$1"
  echo "==> Pushing to $container"
  for dir in "${DIRS[@]}"; do
    echo "    $dir/ → $container:$CONTAINER_BASE/$dir/"
    docker cp "$dir/." "$container:$CONTAINER_BASE/$dir/"
  done
  for file in "${FILES[@]}"; do
    echo "    $file → $container:$CONTAINER_BASE/$file"
    docker cp "$file" "$container:$CONTAINER_BASE/$file"
  done
}

pull_from() {
  local container="$1"
  echo "==> Pulling from $container"
  for dir in "${DIRS[@]}"; do
    echo "    $container:$CONTAINER_BASE/$dir/ → ./$dir/"
    mkdir -p "./$dir"
    docker cp "$container:$CONTAINER_BASE/$dir/." "./$dir/"
  done
  for file in "${FILES[@]}"; do
    echo "    $container:$CONTAINER_BASE/$file → ./$file"
    docker cp "$container:$CONTAINER_BASE/$file" "./$file"
  done
}

[[ $# -lt 1 ]] && usage

ACTION="$1"
TARGET="${2:-all}"

case "$ACTION" in
  push)
    case "$TARGET" in
      frontend)  push_to frontend ;;
      backend)   push_to backend ;;
      all)
        for c in "${CONTAINERS[@]}"; do push_to "$c"; done ;;
      *) usage ;;
    esac
    ;;
  pull)
    case "$TARGET" in
      frontend)  pull_from frontend ;;
      backend)   pull_from backend ;;
      all)
        echo "WARNING: pulling from multiple containers will overwrite. Specify one."
        usage ;;
      *) usage ;;
    esac
    ;;
  *) usage ;;
esac

echo "Done."
