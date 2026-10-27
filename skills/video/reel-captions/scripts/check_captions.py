#!/usr/bin/env python3
"""Validate CAPTIONS-PLATFORMS.md against your caption rules before anything is scheduled.

usage: check_captions.py CAPTIONS-PLATFORMS.md [--config config.json]
Exit 0 = every check passed, 1 = at least one FAIL (each printed with the reason).

Sections are '## <name>'. 'short' feeds tiktok, facebook, threads and youtube_description
unless those have their own section. Lines starting with '# ' are comments.
'keyword:', 'cta:' and 'bio:' header lines override the config for this reel ('none' = no CTA).
Dual endings: when the config has bio_cta + bio_platforms, those platforms must carry the bio line and must not
say "comment" or the keyword (the video exported for them ends on the link-in-bio clip).
"""
import argparse, json, os, re, sys

FALLBACK = {"tiktok": "short", "facebook": "short", "threads": "short", "youtube_description": "short"}


def parse(path):
    head, secs, cur = {}, {}, None
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("## "):
            cur = line[3:].strip().lower(); secs[cur] = []; continue
        if cur is None:
            m = re.match(r"^(keyword|cta|bio):\s*(.*)$", line)
            if m:
                head[m.group(1)] = m.group(2).split("  #")[0].strip()
            continue
        if line.startswith("# "):
            continue
        secs[cur].append(line)
    return head, {k: "\n".join(v).strip() for k, v in secs.items()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("file")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "config.json"))
    a = ap.parse_args()
    if not os.path.exists(a.config):
        sys.exit(f"no config at {a.config}: copy config.example.json to config.json and fill it in")
    cfg = json.load(open(a.config))
    head, s = parse(a.file)
    kw = head.get("keyword", cfg.get("keyword", "none")); cta = head.get("cta", cfg.get("cta", "none"))
    fails = []

    def text(p):
        return s.get(p) or s.get(FALLBACK.get(p, ""), "")

    for req in ["twitter", "youtube_title"] + [p for p in cfg["cta_platforms"] if p not in FALLBACK] + (["short"] if any(p in FALLBACK for p in cfg["cta_platforms"]) else []):
        if req not in s:
            fails.append(f"missing section ## {req}")
    for p, lim in cfg["limits"].items():
        t = text(p)
        if t and len(t) > lim:
            fails.append(f"{p}: {len(t)} chars > {lim}")
    if cta.lower() != "none":
        for p in cfg["cta_platforms"]:
            t = text(p)
            if t and cta not in t:
                fails.append(f"{p}: CTA line missing (exact text: {cta})")
    for p in cfg.get("no_cta_platforms", []):
        t = text(p)
        if cta.lower() != "none" and cta in t:
            fails.append(f"{p}: contains the CTA line")
        if re.search(r"\bcomment\b", t, re.I):
            fails.append(f"{p}: contains the word 'comment'")
        if kw.lower() != "none" and re.search(rf"\b{re.escape(kw)}\b", t):
            fails.append(f"{p}: contains the keyword {kw}")
    bio = head.get("bio", cfg.get("bio_cta", ""))
    for p in cfg.get("bio_platforms", []) if bio and bio.lower() != "none" else []:
        t = text(p)
        if not t:
            fails.append(f"{p}: missing (bio platforms need a section or ## short)")
            continue
        if bio not in t:
            fails.append(f"{p}: bio CTA missing (exact text: {bio})")
        if re.search(r"\bcomment\b", t, re.I):
            fails.append(f"{p}: says 'comment' but this platform gets the link-in-bio ending")
        if kw.lower() != "none" and re.search(rf"\b{re.escape(kw)}\b", t):
            fails.append(f"{p}: contains the keyword {kw} (keyword DMs only work on the cta_platforms)")
    for p in cfg.get("skip_platforms", []):
        if p in s:
            fails.append(f"{p}: section present but this platform is skipped")
    yt = s.get("youtube_title", "")
    if yt != yt.strip() or "\n" in yt:
        fails.append("youtube_title: must be one line, no trailing spaces")
    for p, t in s.items():
        rng = cfg.get("hashtags", {}).get(p, cfg.get("hashtags", {}).get("default"))
        n = len(re.findall(r"(?<!\w)#\w+", t))
        if rng and not (rng[0] <= n <= rng[1]) and p != "youtube_title":
            fails.append(f"{p}: {n} hashtags, want {rng[0]} to {rng[1]}")
        for b in cfg.get("ban", []):
            if b in t:
                fails.append(f"{p}: contains banned character/phrase {b!r}")
    for p in sorted(set(cfg["limits"]) | set(s)):
        t = text(p)
        if t:
            print(f"  {p:<20} {len(t):>5} chars")
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else f"{len(fails)} FAIL(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
