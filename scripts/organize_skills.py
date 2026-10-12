#!/usr/bin/env python3
"""Move every skill into its category folder and rebuild skills/index.json.

    python3 scripts/organize_skills.py          # move + write the index
    python3 scripts/organize_skills.py --check  # exit 1 if anything is out of place

categories.json (repo root) lists which category each skill belongs to.
A skill at skills/<slug>/ moves to skills/<category>/<slug>/ with `git mv`.
Running it again changes nothing, so it is safe to run after merging main.

skills/index.json maps every slug to its folder. johann.fyi's
/go/claude-skills?s=<slug> redirect reads it, so links keep working when a
skill moves. Slugs never change.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
check_only = "--check" in sys.argv

cats = json.loads((ROOT / "categories.json").read_text())
slug_to_cat = {}
for cat, info in cats.items():
    for slug in info["skills"]:
        if slug in slug_to_cat:
            sys.exit(f"{slug} is listed in both {slug_to_cat[slug]} and {cat}")
        slug_to_cat[slug] = cat

problems, moves, index = [], [], {}

# skills still at the top level
for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
    if d.name in cats:
        continue
    if not ((d / "SKILL.md").exists() or (d / "README.md").exists()):
        problems.append(f"skills/{d.name}: not a category and has no SKILL.md or README.md")
        continue
    cat = slug_to_cat.get(d.name)
    if not cat:
        problems.append(f"skills/{d.name}: not listed in categories.json")
        continue
    moves.append((d, SKILLS / cat / d.name))

# skills already inside a category
for cat in cats:
    cdir = SKILLS / cat
    if not cdir.is_dir():
        continue
    for d in sorted(p for p in cdir.iterdir() if p.is_dir()):
        if not ((d / "SKILL.md").exists() or (d / "README.md").exists()):
            problems.append(f"skills/{cat}/{d.name}: no SKILL.md or README.md")
        elif slug_to_cat.get(d.name) != cat:
            problems.append(f"skills/{cat}/{d.name}: categories.json says {slug_to_cat.get(d.name)}")
        else:
            index[d.name] = f"skills/{cat}/{d.name}"

for src, dst in moves:
    index[src.name] = f"skills/{dst.parent.name}/{src.name}"

missing = sorted(set(slug_to_cat) - set(index))

if check_only:
    for src, dst in moves:
        print(f"MOVE  {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    for p in problems:
        print(f"ERROR {p}")
    for m in missing:
        print(f"note  {m}: listed but not in this checkout yet")
    idx_path = SKILLS / "index.json"
    stale = not idx_path.exists() or json.loads(idx_path.read_text()) != dict(sorted(index.items()))
    if stale:
        print("ERROR skills/index.json is missing or out of date")
    ok = not moves and not problems and not stale
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if problems:
    sys.exit("\n".join(problems))
for src, dst in moves:
    dst.parent.mkdir(exist_ok=True)
    subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT, check=True)
    print(f"moved {src.name} -> skills/{dst.parent.name}/")
(SKILLS / "index.json").write_text(json.dumps(dict(sorted(index.items())), indent=2) + "\n")
print(f"index: {len(index)} skills")
for m in missing:
    print(f"note  {m}: listed but not in this checkout yet")

# README: rebuild the skills section between the markers from categories.json
readme = ROOT / "README.md"
text = readme.read_text()
START, END = "<!-- skills:start -->", "<!-- skills:end -->"
if START in text and END in text:
    parts = [START, ""]
    for cat, info in cats.items():
        parts.append(f"### {info['title']} (`skills/{cat}/`)")
        parts.append("")
        if info.get("intro"):
            parts += [info["intro"], ""]
        parts += ["| Skill | What it does | Runs in / from |", "|---|---|---|"]
        for slug, row in info["skills"].items():
            if slug in index:
                parts.append(f"| [{slug}]({index[slug]}) | {row['what']} | {row['notes']} |")
        parts.append("")
    parts.append(END)
    a, b = text.index(START), text.index(END) + len(END)
    rest = text[b:]
    # drop old per-group tables a merge from main may have brought back
    nxt = rest.find("\n## ")
    if nxt != -1:
        rest = rest[nxt:]
    readme.write_text(text[:a] + "\n".join(parts) + "\n" + rest)
    print("README skills section rebuilt")
