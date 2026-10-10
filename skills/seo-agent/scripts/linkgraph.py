#!/usr/bin/env python3
"""Internal-link graph + snapshot diff for the seo-agent skill.

Builds the internal-link graph of a site from its sitemap, snapshots it, and
diffs against the previous snapshot to surface regressions automatically.
This is the rigorous replacement for hand-counted inlinks/orphans.

State lives at ~/.claude/seo-state/<slug>/<YYYY-MM-DD>.json
Stdlib only. No paid API.

Usage:
  python3 linkgraph.py <domain>                # crawl, snapshot, diff vs last
  python3 linkgraph.py <domain> --sample 50    # quick run: sample N sitemap URLs
  python3 linkgraph.py <domain> --no-fetch     # diff the two most recent snapshots
  python3 linkgraph.py <domain> --force        # persist even if >5% of URLs failed to fetch
"""
import sys, os, json, re, urllib.request, datetime, random

UA = "Mozilla/5.0 (seo-agent-linkgraph)"
STATE_DIR = os.path.expanduser("~/.claude/seo-state")
THIN_WORDS = 600  # money-page floor; pages below flagged

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

def text(html):
    for t in ["script", "style", "noscript", "svg"]:
        html = re.sub(r"<%s.*?</%s>" % (t, t), " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", re.sub(r"<[^>]+>", " ", html))

def find(html, pat):
    m = re.search(pat, html, re.I)
    return m.group(1).strip() if m else ""

# ---- sitemap discovery (mirrors crawl.py; kept local to stay self-contained) ----
def sitemap_paths(base, sample=None):
    host = re.sub(r"^https?://", "", base).rstrip("/")
    urls = []
    def consume(xml):
        for u in re.findall(r"<loc>([^<]+)</loc>", xml, re.I):
            u = u.strip()
            if u.endswith(".xml"):
                try: consume(fetch(u, 20))
                except Exception: pass
            else: urls.append(u)
    for c in ["/sitemap.xml", "/sitemap_index.xml", "/sitemaps.xml"]:
        try: consume(fetch(base + c, 20)); break
        except Exception: continue
    paths = []
    for u in urls:
        m = re.match(r"https?://%s(/.*)?$" % re.escape(host), u)
        if m:
            p = m.group(1) or "/"
            paths.append(p if p.startswith("/") else "/" + p)
    seen = set(); out = []
    for p in paths:
        if p not in seen:
            seen.add(p); out.append(p)
    if sample and len(out) > sample:
        random.seed(1); out = sorted(random.sample(out, sample))
    return out

def normalise(href, base, host):
    """Resolve an <a href> to a site-relative path on the same host, or None."""
    href = href.strip().split("#")[0].split("?")[0]
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    host = host.lstrip(".")
    if href.startswith("/"):
        return href
    if href.startswith(("http://", "https://")):
        m = re.match(r"https?://%s(?:[:]?\d*)?(/.*)?$" % re.escape(host), href)
        return (m.group(1) or "/") if m else None
    # relative path, resolve against base
    return None  # rare for these sites; skip rather than guess

def crawl_graph(base, paths):
    host = re.sub(r"^https?://", "", base).rstrip("/").lstrip("www.")  # tolerant
    # actually keep www for matching; recompute properly
    host_full = re.sub(r"^https?://", "", base).rstrip("/")
    outlinks = {}   # path -> set(paths it links to)
    meta = {}       # path -> {title, words, schema}
    for i, p in enumerate(paths, 1):
        try:
            html = fetch(base + p)
        except Exception as e:
            sys.stderr.write("  [%d/%d] ERR %s: %s\n" % (i, len(paths), p, e))
            continue
        if i % 25 == 0 or i == len(paths):
            sys.stderr.write("  [%d/%d] %s\n" % (i, len(paths), p))
        # outlinks
        links = set()
        for href in re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', html, re.I):
            rp = normalise(href, base, host_full)
            if rp:
                links.add(rp)
        outlinks[p] = sorted(links)
        meta[p] = {
            "title": find(html, r"<title>(.*?)</title>")[:140],
            "words": len(text(html).split()),
            "schema": sorted(set(re.findall(r'"@type"\s*:\s*"?([^",\]}]+)"?',
                          " ".join(re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I))))),
        }
    # in-degree
    indeg = {p: 0 for p in paths}
    for src, dsts in outlinks.items():
        for d in dsts:
            if d in indeg:
                indeg[d] += 1
    return outlinks, indeg, meta

MAX_UNFETCHED_FRAC = 0.05  # refuse to persist a crawl with more than 5% fetch failures

def snapshot(base, paths, outlinks, indeg, meta):
    orphans = sorted([p for p in paths if p in indeg and indeg[p] == 0])
    thin = sorted([p for p, m in meta.items() if 0 < m["words"] < THIN_WORDS])
    zero = sorted([p for p in paths if p not in meta])  # unfetched/errored
    host = re.sub(r"^https?://", "", base).rstrip("/")
    return {
        "domain": base,
        "host": host,
        "crawled_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url_count": len(paths),
        "urls": {p: {
                    "in_degree": indeg.get(p, 0),
                    "outlinks": outlinks.get(p, []),
                    "title": meta.get(p, {}).get("title", ""),
                    "words": meta.get(p, {}).get("words", 0),
                    "schema": meta.get(p, {}).get("schema", []),
                 } for p in paths},
        "orphans": orphans,
        "thin_pages": thin,
        "unfetched": zero,
    }

def slug(base):
    return re.sub(r"^https?://", "", base).rstrip("/").replace(".", "_").replace("/", "_")

def save_snapshot(snap):
    d = os.path.join(STATE_DIR, slug(snap["domain"]))
    os.makedirs(d, exist_ok=True)
    today = snap["crawled_at"][:10]
    path = os.path.join(d, today + ".json")
    prev = list_snapshots(snap["domain"])
    with open(path, "w") as f:
        json.dump(snap, f, indent=2, sort_keys=True)
    return path, prev

def list_snapshots(base):
    d = os.path.join(STATE_DIR, slug(base))
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))

def load_snapshot(base, date):
    d = os.path.join(STATE_DIR, slug(base))
    with open(os.path.join(d, date + ".json")) as f:
        return json.load(f)

def diff_snapshots(prev, curr):
    lines = []
    pu, cu = set(prev["urls"]), set(curr["urls"])
    added = sorted(cu - pu)
    removed = sorted(pu - cu)
    if added:
        lines.append("URLS ADDED (%d):" % len(added))
        for u in added[:30]: lines.append("  + " + u)
        if len(added) > 30: lines.append("  ... (%d more)" % (len(added) - 30))
    if removed:
        lines.append("URLS REMOVED (%d):" % len(removed))
        for u in removed[:30]: lines.append("  - " + u)
    # per-URL deltas on the intersection
    inlink_drops, schema_lost, schema_gained, title_changed = [], [], [], []
    for p in sorted(pu & cu):
        a, b = prev["urls"][p], curr["urls"][p]
        if b["in_degree"] < a["in_degree"]:
            inlink_drops.append((p, a["in_degree"], b["in_degree"]))
        if a["title"] and b["title"] and a["title"] != b["title"]:
            title_changed.append((p, a["title"], b["title"]))
        lost = set(a["schema"]) - set(b["schema"])
        gained = set(b["schema"]) - set(a["schema"])
        if lost: schema_lost.append((p, sorted(lost)))
        if gained: schema_gained.append((p, sorted(gained)))
    if inlink_drops:
        lines.append("\nINLINK DROPS (regression risk):")
        for p, old, new in inlink_drops[:30]:
            lines.append("  %s  %d -> %d" % (p, old, new))
    if schema_lost:
        lines.append("\nSCHEMA LOST:")
        for p, types in schema_lost[:20]:
            lines.append("  %s  %s" % (p, types))
    if schema_gained:
        lines.append("\nSCHEMA GAINED (likely yesterday's fixes landing):")
        for p, types in schema_gained[:20]:
            lines.append("  %s  %s" % (p, types))
    if title_changed:
        lines.append("\nTITLE CHANGES:")
        for p, old, new in title_changed[:15]:
            lines.append("  %s\n    was: %s\n    now: %s" % (p, old, new))
    po, co = set(prev["orphans"]), set(curr["orphans"])
    new_orphans = sorted(co - po)
    resolved = sorted(po - co)
    if new_orphans:
        lines.append("\nNEW ORPHANS (in sitemap, 0 internal inlinks):")
        for u in new_orphans[:30]: lines.append("  ! " + u)
    if resolved:
        lines.append("\nORPHANS RESOLVED:")
        for u in resolved[:15]: lines.append("  ok " + u)
    pt, ct = set(prev["thin_pages"]), set(curr["thin_pages"])
    new_thin = sorted(ct - pt)
    if new_thin:
        lines.append("\nNEW THIN PAGES (<%dw):" % THIN_WORDS)
        for u in new_thin[:20]: lines.append("  t " + u)
    if not lines:
        lines.append("No material changes since last snapshot.")
    return "\n".join(lines)

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)
    base = args[0].rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base  # schemeless input made every fetch fail silently
    no_fetch = "--no-fetch" in args
    sample = None
    if "--sample" in args:
        sample = int(args[args.index("--sample") + 1])
    snaps = list_snapshots(base)
    if no_fetch:
        if len(snaps) < 2:
            print("Need >= 2 snapshots to diff; found %d. Run without --no-fetch first." % len(snaps))
            sys.exit(1)
        print(diff_snapshots(load_snapshot(base, snaps[-2]), load_snapshot(base, snaps[-1])))
        return
    paths = sitemap_paths(base, sample=sample)
    sys.stderr.write("Sitemap: %d URLs\n" % len(paths))
    if not paths:
        sys.exit(1)
    outlinks, indeg, meta = crawl_graph(base, paths)
    snap = snapshot(base, paths, outlinks, indeg, meta)
    # Guard: a crawl cut short by a network drop still produced
    # a valid-looking snapshot with hundreds of unfetched URLs, and diffing against
    # it reads as a site-wide inlink collapse. Refuse to persist a snapshot whose
    # fetch-failure rate is above MAX_UNFETCHED_FRAC unless --force is given.
    unfetched = len(snap["unfetched"])
    frac = unfetched / float(snap["url_count"]) if snap["url_count"] else 0.0
    if frac > MAX_UNFETCHED_FRAC and "--force" not in args:
        sys.stderr.write("REFUSED to save snapshot: %d of %d URLs unfetched (%.1f%% > %.0f%% limit). "
                         "Network problem, not a site change. Re-run when stable, or pass --force.\n"
                         % (unfetched, snap["url_count"], frac * 100, MAX_UNFETCHED_FRAC * 100))
        sys.exit(2)
    path, _ = save_snapshot(snap)
    sys.stderr.write("Snapshot saved: %s\n" % path)
    # diff vs previous (most recent that isn't today)
    today = snap["crawled_at"][:10]
    prev_dates = [d for d in snaps if d != today]
    if prev_dates:
        print("# Diff vs %s\n" % prev_dates[-1])
        print(diff_snapshots(load_snapshot(base, prev_dates[-1]), snap))
    else:
        print("# First snapshot (%d URLs, %d orphans, %d thin). No prior to diff.\n"
              % (snap["url_count"], len(snap["orphans"]), len(snap["thin_pages"])))
        print("Top orphan risks: " + ", ".join(snap["orphans"][:15]) or "(none)")

if __name__ == "__main__":
    main()
