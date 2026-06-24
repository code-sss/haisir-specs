#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash) — enforces the repo hard rule:
# NEVER add a Co-Authored-By trailer (e.g. "Co-Authored-By: Claude") to git commits.
#
# Reads the tool-input JSON on stdin, extracts the Bash command, and if it is a
# `git commit` (incl. --amend) whose message string contains "Co-Authored-By",
# exits 2 with a stderr message that is fed back to Claude so it redoes the
# commit without the trailer.
#
# Limitation: only catches messages passed inline via -m (or visible in the
# command string). Messages read from a file (-F file) or stdin (-F - / heredoc)
# are not in the command string and won't be caught here — the
# `attribution.commit: ""` setting in settings.json is the primary prevention
# layer that stops the trailer from being added at all; this hook is a backstop.

set -u

cmd="$(jq -r '.tool_input.command // ""' 2>/dev/null)"

# Only inspect actual git commit invocations.
case "$cmd" in
  *"git commit"*) ;;
  *) exit 0 ;;
esac

if printf '%s' "$cmd" | grep -qi 'co-authored-by'; then
  printf '%s\n' \
    'BLOCKED by .claude/hooks/block-coauthored.sh: this repo has a hard rule — NEVER add a Co-Authored-By trailer (e.g. "Co-Authored-By: Claude ...") to git commit messages.' \
    'Re-run the git commit WITHOUT any Co-Authored-By line. Do not add it back under any circumstance.' >&2
  exit 2
fi

exit 0