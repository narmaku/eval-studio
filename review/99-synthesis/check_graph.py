#!/usr/bin/env python3
"""Validate the review issue graph.

Checks, across all issue files under review/:
  1. Frontmatter parses and `id` matches the filename prefix.
  2. No dangling references (every ID mentioned in a relationship field exists).
  3. Symmetry: depends_on <-> blocks; supersedes <-> superseded_by;
     conflicts_with is mutual.
  4. No cycles in the depends_on graph.
  5. child_of targets exist.

Usage:  python3 review/99-synthesis/check_graph.py
Exit code 0 and a summary on success; non-zero with a list of violations otherwise.
No third-party dependencies (frontmatter parsed by hand: simple `key: [..]` lists).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parents[1]
REL_FIELDS = ("depends_on", "blocks", "supersedes", "superseded_by", "conflicts_with", "related")

ID_RE = re.compile(r"^(ARCH|DUP|CONS|BUG|SEC|PERF|SIMP|TEST|API|DATA|FE|INFRA|DOC)-\d{3}$")


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "-", "#")):
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key in REL_FIELDS:
            inner = val.strip("[]")
            fm[key] = [x.strip() for x in inner.split(",") if x.strip()] if inner else []
        elif key == "child_of":
            fm[key] = None if val in ("null", "~", "") else val
        else:
            fm[key] = val
    return fm


def main() -> int:
    issues: dict[str, dict] = {}
    errors: list[str] = []

    for path in sorted(REVIEW_DIR.glob("[0-9][0-9]-*/*.md")):
        if path.parent.name in ("00-meta", "99-synthesis"):
            continue
        fm = parse_frontmatter(path.read_text())
        iid = fm.get("id", "")
        if not ID_RE.match(iid):
            errors.append(f"{path.name}: missing/invalid id frontmatter ({iid!r})")
            continue
        if not path.name.startswith(iid):
            errors.append(f"{path.name}: filename does not start with id {iid}")
        if iid in issues:
            errors.append(f"{iid}: duplicate id ({path.name})")
        issues[iid] = fm

    known = set(issues)

    # dangling refs
    for iid, fm in issues.items():
        for field in REL_FIELDS:
            for ref in fm.get(field, []):
                if ref not in known:
                    errors.append(f"{iid}.{field}: dangling reference {ref}")
        child = fm.get("child_of")
        if child and child not in known:
            errors.append(f"{iid}.child_of: dangling reference {child}")

    # symmetry
    pairs = [("depends_on", "blocks"), ("supersedes", "superseded_by")]
    for fwd, inv in pairs:
        for iid, fm in issues.items():
            for ref in fm.get(fwd, []):
                if ref in known and iid not in issues[ref].get(inv, []):
                    errors.append(f"asymmetry: {iid}.{fwd} -> {ref}, but {ref}.{inv} lacks {iid}")
            for ref in fm.get(inv, []):
                if ref in known and iid not in issues[ref].get(fwd, []):
                    errors.append(f"asymmetry: {iid}.{inv} -> {ref}, but {ref}.{fwd} lacks {iid}")
    for iid, fm in issues.items():
        for ref in fm.get("conflicts_with", []):
            if ref in known and iid not in issues[ref].get("conflicts_with", []):
                errors.append(f"asymmetry: {iid}.conflicts_with -> {ref} not mutual")

    # depends_on cycles (DFS)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(known, WHITE)

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        for nxt in issues[node].get("depends_on", []):
            if nxt not in known:
                continue
            if color[nxt] == GRAY:
                errors.append(f"depends_on cycle: {' -> '.join(stack + [node, nxt])}")
            elif color[nxt] == WHITE:
                dfs(nxt, stack + [node])
        color[node] = BLACK

    for iid in known:
        if color[iid] == WHITE:
            dfs(iid, [])

    n_edges = sum(len(fm.get(f, [])) for fm in issues.values() for f in ("depends_on", "supersedes", "conflicts_with"))
    superseded = sorted(i for i, fm in issues.items() if fm.get("superseded_by"))

    print(f"issues: {len(issues)}")
    print(f"hard edges (depends_on/supersedes/conflicts_with, directed): {n_edges}")
    print(f"superseded (graph-record) issues: {len(superseded)}: {', '.join(superseded)}")
    if errors:
        print(f"\nVIOLATIONS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("graph OK: no dangling refs, symmetric edges, no depends_on cycles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
