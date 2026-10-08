---
name: describe-current-state
description: Capture what is built today in the three sibling repos into current/{schema,api_contracts,ui_flows}.md (snapshot script → one delta agent per changed repo → approval → apply agent → SHA write). Optionally refreshes docs/*-guide.md. Does not commit.
when_to_use: Use before planning a phase, after closing one, or when the user asks what is built. Triggers - "what's built?", "capture current state", "snapshot the codebase", "what is implemented today", "/describe-current-state".
argument-hint: "[--guides to also refresh docs/*-guide.md]"
---

# Describe Current State

**Context rule:** the main session only orchestrates. It never reads sibling repos, diffs, `current/*.md`, `docs/`, `target/requirements/` bodies, or decisions/phases/progress.md. Subagents read from paths and hand off through `.claude/plans/describe-current-state/` (gitignored). Agent prompts pass paths, never content, and end with the return format given here.

Script: `python3 .claude/skills/describe-current-state/scripts/snapshot.py` (`--files <repo>`, `--write`; scopes are defined in it). Baseline SHAs live only in `current/snapshot_shas.md`.

## 1. Snapshot

Run the script (it also saves the analysed HEADs to `.claude/plans/describe-current-state/range.txt` for step 6). Show the user its output. Repos with `UNCHANGED` or `files=0` need no agent. If every repo is like that, skip to step 5.

## 2. Delta agents (one per remaining repo, all in one message, `general-purpose`, inherited model)

Prompt: repo name, today's date. "Run `python3 .claude/skills/describe-current-state/scripts/snapshot.py --files <repo>`. It prints the RANGE line (mode, range, repo dir, scope) and the changed files. INCREMENTAL: read `git -C <dir> diff <range> -- <files>` in batches. FULL: read the listed files. Then read only the matching sections of the current docs (grep `^##` headings first): backend → `current/schema.md`, `current/api_contracts.md`; frontend → `current/ui_flows.md`; deploy → gateway routes, WAF, body limits and CSP notes in `current/api_contracts.md` and `current/ui_flows.md`. Record only what is implemented and differs from the docs. Ignore refactors with no visible effect on schema, API or UI. Write `.claude/plans/describe-current-state/<repo>.md`:

```
# DELTA <repo> <range>
## Summary
- <file> <+|~|-> <section> — <one line>
## Detail
### <file> → <existing heading, or 'new after <heading>'>
<exact replacement or insertion text in that file's existing style>
```

Return only `DELTA <repo> <n changes>`."

## 3. Approval

For each delta, run `sed -n '1,/^## Detail/p' .claude/plans/describe-current-state/<repo>.md` and show those blocks with the counts.

> **⏸ APPROVAL REQUIRED** — reply **go** to apply, or give corrections.
> Only an explicit user message counts. Never auto-approve, even in auto mode.

**Stop.** Send corrections to a delta agent for that repo to revise its file, then show the summary again.

## 4. Apply agent (`general-purpose`, model `sonnet`)

Prompt: the delta paths and the short HEADs from step 1. "Apply each `## Detail` block verbatim to the named file and heading. Add nothing else. In all three of `current/schema.md`, `current/api_contracts.md`, `current/ui_flows.md` (touched or not), update the `## Snapshot Baseline` table to the new short SHAs and today's date, and delete any 'Next session: run git diff' note. If `Implementation_planning/progress.md` still has a `**Snapshot baseline (current):` line with copied SHAs, replace that line with `> Snapshot baseline: see current/snapshot_shas.md.` Make no other progress.md edits. Return only `git diff --stat -- current Implementation_planning/progress.md`."

## 5. Guides (only with `--guides`, or if the user says yes when asked)

Ask: "Refresh docs/*-guide.md from these deltas?" On yes, spawn a `general-purpose` agent with the delta paths: "Update `docs/{parent,platform-admin,student}-guide.md` only for changes a user of that persona can see (new or changed screen, field or rule; remove features that are gone). Use targeted edits. Never create a guide for a persona that has none. Return only `GUIDE <file> <n edits>` lines, or `GUIDE none`."

## 6. Write SHAs + report

Run the script with `--write`. It writes the HEADs saved in step 1, and prints `REFUSED head moved <repo>` (writing nothing) if a repo HEAD changed since then: tell the user the deltas missed those commits and to rerun from step 1. Otherwise report the mode per repo, the change counts, the diffstat, any guide lines, and the `PLAN` line from step 1. If it says `PLAN DRIFT`, add: "Code has moved past the plan baseline. Run /plan to reconcile before implementing."

Do **not** stage or commit.
