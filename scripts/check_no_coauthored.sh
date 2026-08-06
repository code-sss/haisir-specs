#!/usr/bin/env bash
# Pre-commit commit-msg hook: reject commit messages containing a
# "Co-Authored-By" trailer. Claude Code's default appends this trailer; this
# repo forbids it. The commit-message file path is passed as the first
# argument. Exits 1 on violation (blocks the commit), 0 otherwise.
set -euo pipefail

msg_file="${1:-}"
if [ -z "$msg_file" ]; then
    exit 0
fi

if grep -qF "Co-Authored-By" "$msg_file"; then
    echo "error: commit message contains a forbidden 'Co-Authored-By'" >&2
    echo "error: trailer. Remove it and retry." >&2
    exit 1
fi
