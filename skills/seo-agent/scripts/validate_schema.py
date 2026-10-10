#!/usr/bin/env python3
"""JSON-LD validator for the seo-agent skill.

Catches the regressions the regex-based crawler can't: malformed JSON-LD that
fails to parse (Google silently drops it), and canonical mismatches. Local only
,  no external API dependency. The agent judges completeness; this tool answers
"is the structured data even valid?"

Usage:
  python3 validate_schema.py <url> [<url> ...]
  python3 validate_schema.py https://www.example.com/ https://www.example.com/blog/some-post
"""
import sys, json, re, urllib.request

UA = "Mozilla/5.0 (seo-agent-schema)"
BLOCK_RE = re.compile(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")

def canon(html):
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']*)', html, re.I)
    return m.group(1).strip() if m else ""

def types_in(obj):
    out = []
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, list): out += [str(x) for x in t]
        elif t: out.append(str(t))
        for v in obj.values():
            out += types_in(v)
    elif isinstance(obj, list):
        for v in obj: out += types_in(v)
    return out

def check(url):
    url = url if url.startswith("http") else "https://" + url
    try:
        html = fetch(url)
    except Exception as e:
        print("\n### %s\n  ERR %s" % (url, e)); return
    blocks = BLOCK_RE.findall(html)
    print("\n### %s" % url)
    print("  JSON-LD blocks: %d" % len(blocks))
    if not blocks:
        print("  WARN: no JSON-LD found in initial HTML")
        return
    parsed, types = [], set()
    malformed = 0
    for i, raw in enumerate(blocks, 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            malformed += 1
            print("  BLOCK %d: MALFORMED JSON-LD, %s" % (i, str(e)[:80]))
            print("    snippet: %s" % raw[:120].replace("\n", " "))
            continue
        parsed.append(obj)
        for t in types_in(obj):
            types.add(t)
    c = canon(html)
    print("  valid blocks : %d" % len(parsed))
    print("  @types       : %s" % sorted(types))
    if c:
        # canonical should resolve to this URL (modulo trailing slash / scheme)
        norm = lambda s: s.rstrip("/").replace("http://", "https://")
        match = norm(c) == norm(url) or url.rstrip("/").startswith(norm(c))
        print("  canonical    : %s %s" % (c, "" if match else "(MISMATCH, check!)"))
    if malformed:
        print("  >> %d block(s) failed to parse, Google is dropping this schema." % malformed)

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    for u in sys.argv[1:]:
        check(u)

if __name__ == "__main__":
    main()
