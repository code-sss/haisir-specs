"""Mechanical checks on Implementation_planning/PLAN.md + TASKS.md (format: .claude/references/tasks-plan-contract.md).

Usage: python3 .claude/skills/plan/scripts/plan_tool.py <cmd> [--dir <Implementation_planning dir>]
  lint          OK | ISSUES <n>, then one line per issue (PLAN.md + TASKS.md)
  lint --plan <file>  same, PLAN-only checks on a draft (headings/tags, fields, Depends on, unknown deps, cycles)
  ready [--write]  READY <n>, then the Ready-now bullets; --write rewrites TASKS.md "## Ready now" in place
  stats         STATS line (leaves, nodes, ROOT, archive-eligible), then one line per repo
  drift         DRIFT plan:<n> snapshot:<m> (repos whose HEAD moved), then one line per sibling repo
  selftest      SELFTEST OK (asserts on an inline fixture)
lint/ready/stats print NO_PLAN when neither file exists, PARTIAL <missing file> when only one does.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]  # haisir-specs
REPOS = ("backend", "frontend", "deploy")
ID = r"T\d+p?(?:\.\d+){1,2}[a-z]?"
TAG = r"backend|frontend|deploy|specs|manual"  # manual: parsed for archives, rejected by lint in live plans
FIELDS = ("Build", "Done when", "Test", "Depends on")

P_TASK = re.compile(rf"^##### ({ID}) \[({TAG})\] — (.+)$")
P_NODE = re.compile(r"^(?:## (ROOT) — |## (G\d+) — |### (G\d+\.\d+) — )")
P_FIELD = re.compile(r"^- \*\*(Build|Done when|Test|Depends on)\*\*: ?(.*)$")
P_DEPS = re.compile(rf"^(None|{ID} \[(?:{TAG})\](?:, {ID} \[(?:{TAG})\])*)\.?$")
P_WATER = re.compile(r"^<!-- plan-baseline: backend:([0-9a-f]{7,40}) frontend:([0-9a-f]{7,40}) deploy:([0-9a-f]{7,40}) -->")
T_LEAF = re.compile(rf"^\s*- \[([ xX~])\] ({ID}) \[({TAG})\]: (.+)$")
T_NODE = re.compile(r"^\s*- \[([ xX~])\] \*\*(ROOT|G\d+(?:\.\d+)?): ")
T_BOX = re.compile(r"^\s*[-*+] \[.{0,3}\]")
T_BASE = re.compile(r"^> (\*\*)?Last baselined: backend:`?([0-9a-f]{7,40})`? frontend:`?([0-9a-f]{7,40})`? deploy:`?([0-9a-f]{7,40})`? \((\d{4}-\d{2}-\d{2})")


def parse_plan(text):
    tasks, cur, field, water, nodes, bad = {}, None, None, None, [], []
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("##### T") and not P_TASK.match(line):
            bad.append(f"HEAD {i} task heading needs 'ID [one repo] — name': {line[:70]}")
        if m := P_NODE.match(line):
            nodes.append(m[1] or m[2] or m[3])
        if m := P_TASK.match(line):
            cur = tasks.setdefault(m[1], {"tag": m[2], "name": m[3], "fields": {}, "dup": m[1] in tasks})
            field = None
        elif line.startswith("#"):
            cur = None
        elif cur is not None and (m := P_FIELD.match(line)):
            field = m[1]
            cur["fields"][field] = m[2]
        elif cur is not None and field and line.startswith("  ") and line.strip():
            cur["fields"][field] += " " + line.strip()  # contract: fields wrap via 2-space continuation lines
        else:
            field = None
        if m := P_WATER.match(line):
            water = dict(zip(REPOS, m.groups()))
    for t in tasks.values():
        dep = t["fields"].get("Depends on", "")
        t["deps"] = [] if dep.strip().lower().startswith("none") else re.findall(ID, dep)
        t["deptext"] = dep
    return tasks, water, nodes, bad


def parse_tasks(text):
    leaves, nodes, unmatched, base = {}, {}, [], None
    for i, line in enumerate(text.splitlines(), 1):
        if m := T_LEAF.match(line):
            if m[2] in leaves:
                unmatched.append(f"DUP TASKS.md:{i} {m[2]}")
            leaves[m[2]] = {"box": m[1], "tag": m[3]}
        elif m := T_NODE.match(line):
            nodes[m[2]] = m[1]
        elif T_BOX.match(line):
            unmatched.append(f"UNMATCHED TASKS.md:{i} {line.strip()[:80]}")
        if base is None and (m := T_BASE.match(line)):
            base = m.groups()[1:]
    return leaves, nodes, unmatched, base


def done(box):
    return box in "xX"


def load(d):
    plan, water, _, _ = parse_plan((d / "PLAN.md").read_text())
    return (plan, water, *parse_tasks((d / "TASKS.md").read_text()), d)


def lint_plan(text):
    """PLAN-only checks — runs on a draft before approval and inside lint()."""
    plan, _, _, issues = parse_plan(text)
    for tid, t in plan.items():
        if t["dup"]:
            issues.append(f"DUP PLAN.md {tid}")
        if t["tag"] == "manual":
            issues.append(f"MANUAL {tid} — [manual] is for archives only")
        for f in FIELDS:
            if f not in t["fields"]:
                issues.append(f"FIELD {tid} missing {f}")
            elif not t["fields"][f].strip():
                issues.append(f"FIELD {tid} empty {f}")
        if t["fields"].get("Depends on", "").strip() and not P_DEPS.match(t["deptext"].strip()):
            issues.append(f"DEPS {tid} not 'None' or 'ID [repo], …': {t['deptext'].strip()[:60]}")
        for dep in t["deps"]:
            if dep not in plan:
                issues.append(f"UNKNOWN_DEP {tid} -> {dep}")
    state = {}  # 1 = visiting, 2 = done

    def visit(tid, path):
        state[tid] = 1
        for dep in plan[tid]["deps"]:
            if state.get(dep) == 1:
                issues.append("CYCLE " + " -> ".join(path[path.index(dep):] + [dep]))
            elif dep in plan and dep not in state:
                visit(dep, path + [dep])
        state[tid] = 2

    for tid in plan:
        if tid not in state:
            visit(tid, [tid])
    return issues


def lint(d):
    text = (d / "PLAN.md").read_text()
    plan, water, pnodes, _ = parse_plan(text)
    _, _, leaves, nodes, unmatched, base, _ = load(d)
    issues = lint_plan(text) + unmatched
    if water is None:
        issues.append("MISSING PLAN.md plan-baseline watermark")
    if base is None:
        issues.append("MISSING TASKS.md 'Last baselined' line")
    n = len(READY_RE.findall((d / "TASKS.md").read_text()))
    if n != 1:
        issues.append("MISSING TASKS.md '## Ready now' heading" if not n else f"DUPLICATE TASKS.md '## Ready now' heading x{n}")
    for tid, t in plan.items():
        if tid not in leaves:
            issues.append(f"MISSING_IN_TASKS {tid}")
        elif leaves[tid]["tag"] != t["tag"]:
            issues.append(f"TAG {tid} plan={t['tag']} tasks={leaves[tid]['tag']}")
    issues += [f"MISSING_IN_PLAN {tid}" for tid in leaves if tid not in plan]
    issues += [f"NODE_MISSING {n} (no TASKS.md node row)" for n in pnodes if n not in nodes]
    return issues


def ready(d):
    plan, _, leaves, nodes, _, _, _ = load(d)
    out = []
    for tid, t in plan.items():
        if tid in leaves and leaves[tid]["box"] == " " and all(done(leaves.get(x, {}).get("box", " ")) for x in t["deps"]):
            deps = ", ".join(f"{x} [{plan.get(x, {}).get('tag', '?')}]" for x in t["deps"])  # IDs only: notes never leak into the bullet
            out.append(f"- {tid} [{t['tag']}]: {t['name']} " + (f"(depends on {deps})" if deps else "(no deps)"))
    if not out:
        open_n = sum(1 for v in leaves.values() if not done(v["box"]))
        if open_n:
            why = f"{open_n} open leaf tasks, all blocked on unchecked dependencies"
        elif "ROOT" not in nodes:  # consistent with stats: absent ROOT row is never archive-eligible
            why = f"all {len(leaves)} leaf tasks are done; ROOT row missing in TASKS.md"
        elif not done(nodes["ROOT"]):
            why = f"all {len(leaves)} leaf tasks are done; ROOT acceptance test pending"
        else:
            why = "all leaf tasks and ROOT done (archive-eligible)"
        out = [f"- None ready — {why}."]
    return out


READY_RE = re.compile(r"^## Ready now\b.*$", re.M)  # decorated headings ("## Ready now (recomputed …)") count too


def write_ready(d, lines):
    p = d / "TASKS.md"
    text = p.read_text()
    m = READY_RE.search(text)
    body = "\n" + "\n".join(lines) + "\n"
    if not m:
        p.write_text(text.rstrip("\n") + "\n\n## Ready now\n" + body)
        return
    nxt = re.search(r"^## ", text[m.end():], re.M)
    rest = text[m.end() + nxt.start():] if nxt else ""
    p.write_text(text[: m.end()] + "\n" + body + ("\n" + rest if rest else ""))


def stats(d):
    _, _, leaves, nodes, _, _, _ = load(d)
    leaf_done = sum(done(v["box"]) for v in leaves.values())
    root = "absent" if "ROOT" not in nodes else ("done" if done(nodes["ROOT"]) else "open")
    eligible = leaves and leaf_done == len(leaves) and root == "done"  # absent ROOT row is never eligible
    lines = [f"STATS leaves {leaf_done}/{len(leaves)} nodes {sum(map(done, nodes.values()))}/{len(nodes)} ROOT {root} archive-eligible {'yes' if eligible else 'no'}"]
    for tag in sorted({v["tag"] for v in leaves.values()}):
        vs = [v for v in leaves.values() if v["tag"] == tag]
        n = sum(done(v["box"]) for v in vs)
        lines.append(f"{tag} done {n} open {len(vs) - n}")
    return lines


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(ROOT_DIR.parent / f"haisir-{repo}"), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def drift(d):
    water = parse_plan((d / "PLAN.md").read_text())[1] if (d / "PLAN.md").exists() else None
    snap = {}
    sp = ROOT_DIR / "current" / "snapshot_shas.md"
    if sp.exists():
        snap = dict(re.findall(r"haisir-(\w+): ([0-9a-f]{7,40})", sp.read_text()))
    moved, lines = {"plan": 0, "snapshot": 0}, []
    for repo in REPOS:
        head = git(repo, "rev-parse", "HEAD")
        if not head:
            lines.append(f"{repo} ERR no git repo at ../haisir-{repo}")
            continue
        parts = [f"{repo} head={head[:7]}"]
        for label, sha in (("plan", (water or {}).get(repo)), ("snapshot", snap.get(repo))):
            if not sha:
                parts.append(f"{label}=none")
                continue
            files = git(repo, "diff", "--name-only", f"{sha}..HEAD")
            if files is None:
                parts.append(f"{label}={sha[:7]}(unknown-sha)")
            else:
                n = len(files.splitlines())
                moved[label] += not head.startswith(sha)
                parts.append(f"{label}={sha[:7]}(+{n} files)")
        lines.append(" ".join(parts))
    return [f"DRIFT plan:{moved['plan']} snapshot:{moved['snapshot']}"] + lines


FIX_PLAN = """# PLAN — Fixture
## ROOT — r
## G1 — g
### G1.1 — s
##### T1.1 [backend] — a
- **Build**: x
- **Done when**: x
- **Test**: x
- **Depends on**: None
##### T1.2 [frontend] — b
- **Build**: x
- **Done when**: x
- **Test**: x
- **Depends on**: T1.1 [backend]
##### T1.1.3 [specs] — c
- **Build**: x
- **Done when**: x
- **Test**: x
- **Depends on**: None
<!-- plan-baseline: backend:aaaaaaa frontend:bbbbbbb deploy:ccccccc -->
"""
FIX_TASKS = """# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> **Last baselined: backend:`aaaaaaa` frontend:`bbbbbbb` deploy:`ccccccc` (2026-01-01)** — legacy form

## G1 [backend][frontend][specs]: g
- [x] T1.1 [backend]: a (2026-01-02)
- [ ] T1.2 [frontend]: b (depends on T1.1 [backend])
- [ ] T1.1.3 [specs]: c
- [ ] **G1.1: s** — integration test
- [ ] **G1: g** — E2E test
---
- [ ] **ROOT: r** — acceptance test

## Ready now

old prose
"""


def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "PLAN.md").write_text(FIX_PLAN)
        (d / "TASKS.md").write_text(FIX_TASKS)
        assert lint(d) == [], lint(d)
        r = ready(d)
        assert r == ["- T1.2 [frontend]: b (depends on T1.1 [backend])", "- T1.1.3 [specs]: c (no deps)"], r
        write_ready(d, r)
        write_ready(d, r)  # idempotent
        t = (d / "TASKS.md").read_text()
        assert t.endswith("## Ready now\n\n" + "\n".join(r) + "\n") and "old prose" not in t, t
        for head in ("## Ready now (recomputed 2026-10-01)\n", "## Ready now"):  # decorated / no trailing newline: replaced, not duplicated
            (d / "TASKS.md").write_text(t.split("## Ready now")[0] + head)
            write_ready(d, r)
            assert (d / "TASKS.md").read_text().endswith(head.rstrip("\n") + "\n\n" + "\n".join(r) + "\n") and lint(d) == [], (d / "TASKS.md").read_text()
        (d / "TASKS.md").write_text(t + "\n## Ready now\n")
        assert lint(d) == ["DUPLICATE TASKS.md '## Ready now' heading x2"], lint(d)
        (d / "TASKS.md").write_text(t)
        assert stats(d)[0] == "STATS leaves 1/3 nodes 0/3 ROOT open archive-eligible no", stats(d)
        (d / "TASKS.md").write_text(t.replace("[ ] T", "[x] T"))
        assert ready(d) == ["- None ready — all 3 leaf tasks are done; ROOT acceptance test pending."], ready(d)
        (d / "PLAN.md").write_text(FIX_PLAN.replace("Depends on**: None\n##### T1.2", "Depends on**: T1.2 [frontend]\n##### T1.2", 1)
                                   .replace("##### T1.1.3 [specs] — c\n- **Build**: x\n", "##### T1.1.3 [deploy] — c\n"))
        (d / "TASKS.md").write_text(t + "- [ ] T9.9 [backend]: ghost\n* [ ] stray\n")
        got = sorted(i.split()[0] for i in lint(d))
        assert got == ["CYCLE", "FIELD", "MISSING_IN_PLAN", "TAG", "UNMATCHED"], lint(d)
        # wrapped Depends on (2-space continuation) keeps the second ID; G-refs / notes are lint errors
        (d / "TASKS.md").write_text(FIX_TASKS)
        (d / "PLAN.md").write_text(FIX_PLAN.replace("T1.1 [backend]\n", "T1.1 [backend],\n  T1.1.3 [specs]\n", 1))
        assert lint(d) == [] and ready(d) == ["- T1.1.3 [specs]: c (no deps)"], (lint(d), ready(d))
        (d / "PLAN.md").write_text(FIX_PLAN.replace("T1.1 [backend]\n", "T1.1 [backend], G3\n  (note)\n", 1))
        assert [i.split()[0] for i in lint(d)] == ["DEPS"], lint(d)
        assert ready(d)[0] == "- T1.2 [frontend]: b (depends on T1.1 [backend])", ready(d)
        # untagged / double-tagged heading, [manual], empty field → PLAN-only lint on a draft (no watermark needed)
        draft = (FIX_PLAN.replace("##### T1.2 [frontend] — b", "##### T1.2 — b").replace("##### T1.1.3 [specs]", "##### T1.1.3 [specs][deploy]")
                 .replace("##### T1.1 [backend]", "##### T1.1 [manual]"))
        got = [i.split()[0] for i in lint_plan(draft)]
        assert got == ["HEAD", "HEAD", "MANUAL"], lint_plan(draft)
        assert lint_plan(FIX_PLAN.replace("- **Done when**: x", "- **Done when**: ", 1).split("<!--")[0]) == ["FIELD T1.1 empty Done when"]
        # PLAN goal/subgoal/ROOT without a TASKS node row; absent ROOT row is never archive-eligible
        (d / "PLAN.md").write_text(FIX_PLAN)
        (d / "TASKS.md").write_text(FIX_TASKS.replace("[ ] T", "[x] T").replace("- [ ] **ROOT: r** — acceptance test\n", "").replace("- [ ] **G1.1: s** — integration test\n", ""))
        assert sorted(lint(d)) == ["NODE_MISSING G1.1 (no TASKS.md node row)", "NODE_MISSING ROOT (no TASKS.md node row)"], lint(d)
        assert stats(d)[0].endswith("ROOT absent archive-eligible no"), stats(d)
        assert ready(d) == ["- None ready — all 3 leaf tasks are done; ROOT row missing in TASKS.md."], ready(d)
        assert status(d) is None
        (d / "TASKS.md").unlink()
        assert status(d) == "PARTIAL missing TASKS.md (do not overwrite PLAN.md unarchived)", status(d)
        (d / "PLAN.md").unlink()
        assert status(d) == "NO_PLAN"
    return ["SELFTEST OK"]


def status(d):
    have = [f for f in ("PLAN.md", "TASKS.md") if (d / f).exists()]
    if len(have) == 2:
        return None
    if not have:
        return "NO_PLAN"  # normal after archive
    return f"PARTIAL missing {'TASKS.md' if have == ['PLAN.md'] else 'PLAN.md'} (do not overwrite {have[0]} unarchived)"


def main(argv):
    if not argv or argv[0] not in ("lint", "ready", "stats", "drift", "selftest"):
        sys.exit(__doc__)
    d = Path(argv[argv.index("--dir") + 1]) if "--dir" in argv else ROOT_DIR / "Implementation_planning"
    cmd = argv[0]
    if cmd == "lint" and "--plan" in argv:
        issues = lint_plan(Path(argv[argv.index("--plan") + 1]).read_text())
        out = [f"ISSUES {len(issues)}" if issues else "OK"] + issues
    elif cmd in ("lint", "ready", "stats") and status(d):
        out = [status(d)]
    elif cmd == "lint":
        issues = lint(d)
        out = [f"ISSUES {len(issues)}" if issues else "OK"] + issues
    elif cmd == "ready":
        r = ready(d)
        if "--write" in argv:
            write_ready(d, r)
        out = [f"READY {sum(not x.startswith('- None') for x in r)}" + (" WROTE TASKS.md" if "--write" in argv else "")] + r
    else:
        out = {"stats": stats, "drift": drift, "selftest": lambda _=None: selftest()}[cmd](d)
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1:])
