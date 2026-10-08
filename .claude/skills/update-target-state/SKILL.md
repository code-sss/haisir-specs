---
name: update-target-state
description: Change the near-term product requirements in target/requirements/ through gather agent → discussion → challenger → approval → writer agent, recording the outcome in decisions.md, progress.md Target State and, when needed, constraints.md. Does not commit.
when_to_use: Use only when the user explicitly wants to add, change or remove a product requirement in target/requirements/ (data model, API contract, business rule, permission, persona flow, UI spec). Not for capturing what is built (/describe-current-state), phase planning (/plan), vision/ edits, or edits to other files. Triggers - "change the target spec for X", "add a requirement", "revise the parent flow", "update target state", "/update-target-state".
argument-hint: "[area or change summary]"
---

# Update Target State

**Context rule:** the main session only orchestrates. It never reads `target/requirements/` bodies, `current/*.md`, prototypes, or decisions/phases/progress/constraints.md. Subagents read from paths and hand off through `.claude/plans/update-target-state/<slug>/` (gitignored). Agent prompts pass paths, never content, and end with the return format given here. Policy lives in CLAUDE.md Critical Rules, facts on the ground in `Implementation_planning/constraints.md`. Link them; don't restate them.

## 1. Scope + deferred-persona guard

Choose a short kebab-case `<slug>` from `$ARGUMENTS` or the user's request. Run `grep -l '⚠ DEFERRED' vision/requirements/*.md`. If the topic touches a listed persona (today: teacher/tutor, institution admin), **stop**. Tell the user that persona is on hold per decisions.md 2026-07-27, and that its vision file must be revised and the banner removed before target state can be defined. Ask whether to do that revision now as its own discussion, or drop the topic.

## 2. Gather agent (`general-purpose`, inherited model)

Prompt: slug, topic. "Build a brief for this topic. For each file, grep `^#` headings and read only the relevant sections. Sources:
- `target/requirements/00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`, plus the topic's own target files.
- `target/requirements/ui-mapping/`.
- For stubs (`grep -l 'Status: stub' target/requirements/*.md`, plus the 6-line `06_institution_admin.md`), use the vision file on the same topic. Numbering diverges (target 08 = essay grading, but vision 08 = hAITU = target 11; target 12–17 and `05_06_07_personas.md` have no vision twin), so match by title, never by number.
- Prototypes: `target/prototypes/*.html` are authoritative where a flow exists (admin, parent, student). Use `vision/prototypes/` only for other personas. Never read a whole HTML file. Grep `id=\"<prefix>-` for screen IDs and read about 40 lines around the ones you need.
- What is built: the relevant sections of `current/{schema,api_contracts,ui_flows}.md` and `Implementation_planning/constraints.md`.
Write `.claude/plans/update-target-state/<slug>/context.md` with the sections `## Schema`, `## API`, `## UI`, `## Built today / constraints` and `## Gaps / ambiguities`. Use at most 12 bullets per section and give a `file:line` ref on each. Return only `WROTE <path> <n gaps>`."

## 3. Discuss (main)

Read `context.md` and present it. Ask what to add, change or remove. Ask clarifying questions and flag conflicts with CLAUDE.md Critical Rules. **Write nothing** until the user says the discussion is finished ("done", "finalise", "update it").

Then write `.claude/plans/update-target-state/<slug>/changes.md`. Give one bullet per agreed change: target file, section, what changes, and why. Mark business-rule and API-contract changes `[PO+lead]`, since CLAUDE.md's Spec Update Convention requires sign-off from both.

## 4. Challenger (`general-purpose`, inherited model)

Prompt: the paths of changes.md and context.md. "Check the proposed changes against CLAUDE.md Critical Rules, `Implementation_planning/constraints.md`, the relevant sections of `current/*.md` (what is already built) and the target files they touch. Look for: rule conflicts; inconsistency with the data model or auth spec; breaking what is built without saying so; effects on other personas or on the current PLAN and phase; whether a new implementation-reality constraint arises. Write `.claude/plans/update-target-state/<slug>/review.md` with these sections: `## Blocking`, `## Minor`, `## New constraint` (or `none`), and `## Phase/TASKS impact` (or `none`). Return only `REVIEW <n blocking> <n minor>`."

## 5. Approval

Read `review.md` and present it.

> **⏸ APPROVAL REQUIRED** — reply **go** to write, or give changes.
> Only an explicit user message counts. Never auto-approve, even in auto mode. Blocking findings get discussed first.

**Stop.** On feedback, update changes.md (re-run step 4 if the change is material) and ask again.

## 6. Writer agent (`general-purpose`, inherited model)

Prompt: the paths of changes.md and review.md, and today's date. "Apply the approved changes:
1. Edit only the target/requirements files named, and only the sections named. Keep everything else unchanged.
2. Prepend to `Implementation_planning/decisions.md` (newest first, below the header) `## <date> — <title> (\`/update-target-state\`)` with the decision and why, in the style of the entries already there.
3. If review.md names a new constraint, add or amend a `## <area> — <fact>` entry in `Implementation_planning/constraints.md`.
4. In `Implementation_planning/progress.md` `## Target State`, append one paragraph for this change, or amend the existing paragraph on the same topic. Never replace the section.
5. Only if review.md's Phase/TASKS impact is not `none`: add a note to `Implementation_planning/phases.md` (next-phase stub or backlog), or flag the affected open task in TASKS.md. Otherwise leave both alone.
Return only a `## Changes made` list (`- <file>: <one line what and why>`)."

## 7. Report

Relay the writer's `## Changes made` list, the challenger's blocking items and how each was resolved, and any `[PO+lead]` items that still need sign-off. Do **not** stage or commit.
