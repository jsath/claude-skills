#!/usr/bin/env python3
"""Lightweight SEO crawler used by the seo-agent skill.
Free, no API. Pulls the SEO-critical elements off a set of URLs so the agent
can audit without a paid tool.

Two modes:
  1. Explicit paths (original behaviour):
       python3 crawl.py <domain> <url_path> [<url_path> ...]
       python3 crawl.py https://www.example.com / /pricing /blog/some-post
  2. Auto-enumerate from sitemap:
       python3 crawl.py --sitemap <domain> [--sample N]
       python3 crawl.py --sitemap https://www.example.com --sample 20
"""
import sys, urllib.request, re, random

UA = "Mozilla/5.0 (seo-agent-crawler)"

def fetch(base, path, timeout=25):
    req = urllib.request.Request(base + path, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

def fetch_url(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

def text(html):
    for t in ["script", "style", "noscript", "svg"]:
        html = re.sub(r"<%s.*?</%s>" % (t, t), " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()

def find(html, pat):
    m = re.search(pat, html, re.I)
    return m.group(1).strip() if m else ""

def audit_page(base, path):
    """Return a dict of SEO fields for one path. Raises on fetch error."""
    h = fetch(base, path)
    title = find(h, r"<title>(.*?)</title>")
    desc = find(h, r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)')
    canon = find(h, r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']*)')
    robots = find(h, r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']*)')
    h1 = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()
          for x in re.findall(r"<h1[^>]*>(.*?)</h1>", h, re.I | re.S)]
    ld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h, re.S | re.I)
    types = []
    for b in ld:
        types += re.findall(r'"@type"\s*:\s*"?([^",\]}]+)"?', b)
    return {
        "path": path,
        "title": title,
        "desc": desc,
        "canon": canon,
        "robots": robots or "(index,follow implied)",
        "words": len(text(h).split()),
        "h1": h1[:2],
        "schema": sorted(set(types)),
    }

def render(d):
    print("\n### %s" % d["path"])
    print("  TITLE : %s" % d["title"][:115])
    print("  DESC  : %s" % d["desc"][:150])
    print("  CANON : %s" % d["canon"])
    print("  ROBOTS: %s" % d["robots"])
    print("  WORDS : %d" % d["words"])
    print("  H1    : %s" % d["h1"])
    print("  SCHEMA: %s" % d["schema"])

def sitemap_urls(base, sample=None):
    """Pull <loc> URLs from sitemap.xml; recurse one level into sitemap indexes.
    Returns site-relative paths."""
    candidates = ["/sitemap.xml", "/sitemap_index.xml", "/sitemaps.xml"]
    urls = []
    seen_idx = set()
    def consume(xml):
        locs = re.findall(r"<loc>([^<]+)</loc>", xml, re.I)
        for u in locs:
            u = u.strip()
            if u.endswith(".xml") and u not in seen_idx:
                seen_idx.add(u)
                try:
                    consume(fetch_url(u, timeout=20))
                except Exception:
                    pass  # nested index unreachable; skip quietly
            else:
                urls.append(u)
    for c in candidates:
        try:
            consume(fetch(base, c, timeout=20))
            break
        except Exception:
            continue
    if not urls:
        sys.stderr.write("No sitemap found at %s (tried %s)\n" % (base, ", ".join(candidates)))
    # normalise to site-relative paths
    host = re.sub(r"^https?://", "", base).rstrip("/")
    paths = []
    for u in urls:
        m = re.match(r"https?://%s(/.*)?$" % re.escape(host), u)
        if m:
            p = m.group(1) or "/"
            if not p.startswith("/"):
                p = "/" + p
            paths.append(p)
    # dedupe preserving order
    seen = set(); out = []
    for p in paths:
        if p not in seen:
            seen.add(p); out.append(p)
    if sample and len(out) > sample:
        random.seed(1)  # deterministic sample for reproducible runs
        out = sorted(random.sample(out, sample))
    return out

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)
    if args[0] == "--sitemap":
        if len(args) < 2:
            print(__doc__); sys.exit(1)
        base = args[1].rstrip("/")
        if not base.startswith("http"):
            base = "https://" + base  # schemeless input made every fetch fail silently
        sample = None
        if "--sample" in args:
            i = args.index("--sample")
            sample = int(args[i + 1])
        paths = sitemap_urls(base, sample=sample)
        sys.stderr.write("Sitemap: %d URLs%s\n" % (len(paths), (" (sample %d)" % sample) if sample else ""))
    else:
        base = args[0].rstrip("/")
        if not base.startswith("http"):
            base = "https://" + base
        paths = args[1:]
    if not paths:
        sys.stderr.write("No paths to crawl.\n"); sys.exit(1)
    for p in paths:
        try:
            render(audit_page(base, p))
        except Exception as e:
            print("\n### %s\n  ERR %s" % (p, e))  # fixed: was printing path twice

if __name__ == "__main__":
    main()
