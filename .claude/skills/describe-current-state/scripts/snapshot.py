#!/usr/bin/env python3
"""Compare current/snapshot_shas.md against sibling repo HEADs (scoped to what current/*.md describes).

Usage (from repo root):
  python3 .claude/skills/describe-current-state/scripts/snapshot.py            # mode per repo + per-dir counts + PLAN drift; saves HEADs to range.txt
  python3 .claude/skills/describe-current-state/scripts/snapshot.py --files R  # R=backend|frontend|deploy: RANGE line + scoped changed files
  python3 .claude/skills/describe-current-state/scripts/snapshot.py --write    # rewrite current/snapshot_shas.md with the range.txt HEADs + today;
                                                                               # `REFUSED head moved <repo>` if a HEAD changed since
  python3 .claude/skills/describe-current-state/scripts/snapshot.py --selftest

Output: first line `OK baseline <date>` | `NO_BASELINE` | `ERROR <msg>`, then per repo
`<repo> UNCHANGED|INCREMENTAL|FULL <base>..<head> files=<n>` with indented `<dir> <n>` counts,
then `PLAN MATCH | PLAN DRIFT <repos> | PLAN NONE`.
"""
import datetime
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SNAP = ROOT / "current" / "snapshot_shas.md"
PLAN = ROOT / "Implementation_planning" / "PLAN.md"
RANGE = ROOT / ".claude" / "plans" / "describe-current-state" / "range.txt"  # HEADs analysed in step 1
REPOS = ("backend", "frontend", "deploy")
# Scopes = what current/{schema,api_contracts,ui_flows}.md describe. Tests live outside these trees.
# ponytail: deploy scope is gateway/auth surface only; scripts, monitoring, staging/prod overrides are out of scope.
SCOPES = {
    "backend": ["src", "alembic/versions"],
    "frontend": ["src", "next.config.ts", ":(exclude)src/styles"],
    "deploy": ["common/apisix_conf", "common/plugin_configs", "common/plugins", "common/routes",
               "common/keycloak", "common/docker-compose.yml", "dev/apisix_conf", "dev/routes",
               "dev/docker-compose.yml", "gateway-docker", ":(exclude)*.md"],
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(ROOT.parent / f"haisir-{repo}"), *args],
                          capture_output=True, text=True)


def parse_snapshot(text):
    shas = dict(re.findall(r"^- haisir-(\w+): ([0-9a-f]{7,40})\s*$", text, re.M))
    date = re.search(r"^- captured: (\S+)", text, re.M)
    return shas, date.group(1) if date else None


def parse_plan(text):
    m = re.findall(r"plan-baseline: (.*?)-->", text)
    return dict(re.findall(r"(\w+):([0-9a-f]+)", m[-1])) if m else None


def mode(base, head, reachable):
    if not base or not reachable:
        return "FULL"
    return "UNCHANGED" if head.startswith(base) else "INCREMENTAL"


def files(repo, base, head, m):
    if m == "UNCHANGED":
        return []
    args = ["ls-files"] if m == "FULL" else ["diff", "--name-only", f"{base}..{head}"]
    return [f for f in git(repo, *args, "--", *SCOPES[repo]).stdout.splitlines() if f]


def state(shas):
    out = {}
    for r in REPOS:
        head = git(r, "rev-parse", "HEAD").stdout.strip()
        if not head:
            sys.exit(f"ERROR cannot read HEAD of ../haisir-{r}")
        base = shas.get(r)
        reachable = bool(base) and git(r, "cat-file", "-e", f"{base}^{{commit}}").returncode == 0
        m = mode(base, head, reachable)
        out[r] = (base, head, m, files(r, base, head, m))
    return out


def moved(recorded, st):
    return [r for r in REPOS if recorded.get(r) != st[r][1]]


def selftest():
    shas, date = parse_snapshot("## Snapshot SHAs\n- haisir-backend: abc1234\n- haisir-deploy: 0123456789\n- captured: 2026-08-18\n")
    assert shas == {"backend": "abc1234", "deploy": "0123456789"} and date == "2026-08-18"
    assert parse_plan("x\n<!-- plan-baseline: backend:aa frontend:bb deploy:cc -->\n") == {"backend": "aa", "frontend": "bb", "deploy": "cc"}
    assert parse_plan("no watermark") is None
    assert mode(None, "abc", False) == "FULL" and mode("abc", "abcdef", True) == "UNCHANGED"
    assert mode("abc", "def", True) == "INCREMENTAL" and mode("abc", "def", False) == "FULL"
    st = {"backend": (None, "a" * 40, "", []), "frontend": (None, "b" * 40, "", []), "deploy": (None, "c" * 40, "", [])}
    assert moved({"backend": "a" * 40, "frontend": "b" * 40, "deploy": "c" * 40}, st) == []
    assert moved({"backend": "a" * 40, "frontend": "x" * 40}, st) == ["frontend", "deploy"]
    print("SELFTEST OK")


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    shas, date = parse_snapshot(SNAP.read_text()) if SNAP.exists() else ({}, None)
    st = state(shas)
    if argv[:1] == ["--write"]:
        if not RANGE.exists():
            sys.exit(f"REFUSED no {RANGE.relative_to(ROOT)} (run the script without --write first)")
        recorded = dict(re.findall(r"^(\w+) ([0-9a-f]{40})$", RANGE.read_text(), re.M))
        if bad := moved(recorded, st):  # snapshot_shas.md must record what was analysed, not HEAD at write time
            sys.exit("REFUSED head moved " + " ".join(bad) + " (rerun from step 1)")
        lines = ["## Snapshot SHAs"] + [f"- haisir-{r}: {st[r][1]}" for r in REPOS]
        SNAP.write_text("\n".join(lines + [f"- captured: {datetime.date.today()}", ""]))
        return print(f"WROTE {SNAP.relative_to(ROOT)} " + " ".join(f"{r}:{st[r][1][:7]}" for r in REPOS))
    if argv[:1] == ["--files"]:
        r = argv[1] if len(argv) > 1 else ""
        if r not in st:
            sys.exit("ERROR --files needs backend|frontend|deploy")
        base, head, m, fs = st[r]
        print(f"RANGE {r} {m} {(base or '')[:7]}..{head[:7]} dir=../haisir-{r} scope={' '.join(SCOPES[r])}")
        return print("\n".join(fs)) if fs else None
    RANGE.parent.mkdir(parents=True, exist_ok=True)
    RANGE.write_text("".join(f"{r} {st[r][1]}\n" for r in REPOS))
    print(f"OK baseline {date}" if shas else "NO_BASELINE")
    for r in REPOS:
        base, head, m, fs = st[r]
        print(f"{r} {m} {(base or '-')[:7]}..{head[:7]} files={len(fs)}")
        for d, n in sorted(Counter("/".join(f.split("/")[:2]) for f in fs).items()):
            print(f"  {d} {n}")
    plan = parse_plan(PLAN.read_text()) if PLAN.exists() else None
    if not plan:
        return print("PLAN NONE")
    drift = [r for r in REPOS if not st[r][1].startswith(plan.get(r, "-"))]
    print("PLAN DRIFT " + " ".join(f"{r}:{plan.get(r, '-')[:7]}->{st[r][1][:7]}" for r in drift) if drift else "PLAN MATCH")


if __name__ == "__main__":
    main(sys.argv[1:])
