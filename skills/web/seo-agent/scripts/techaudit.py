#!/usr/bin/env python3
"""Deep technical SEO audit for the seo-agent skill. Stdlib only, read-only.

One command crawls a site (sitemap seeds + link discovery from the homepage),
follows every redirect hop by hand, and checks crawlability, indexability,
head/meta, structured data, security/infra headers and AI-crawler access.
Every finding comes out as: rule, severity, evidence (URL + observed value),
fix, effort, owner. Rendering (raw vs JS DOM) lives in render_check.py and
Core Web Vitals in cwv.py; this script covers everything that needs no browser.

Usage:
  python3 techaudit.py <domain> --out DIR [--max 1500] [--workers 8]
                       [--preview-host foo.vercel.app ...] [--probe /api/x ...]
                       [--depth-limit 4] [--thin 250]
Outputs (DIR):
  pages.jsonl        one record per fetched URL (status, chain, headers, meta, links, schema)
  edges.tsv          internal link graph (src, dst, anchor, nofollow)
  site-checks.json   robots, sitemap, host variants, infra, AI crawlers, probes
  issues.json        [{rule, severity, title, count, evidence[], fix, effort, owner}]
  issues.md          the same, as a severity-sorted table
Re-runnable; writes pages.jsonl incrementally so a killed run keeps its data.
"""
import sys, os, re, json, gzip, zlib, time, hashlib, random, string, subprocess
import urllib.request, urllib.parse, urllib.error, http.client, ssl
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from collections import defaultdict, Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (compatible; seo-agent-techaudit/1.0; +https://github.com/jsath/claude-skills)"
GOOGLEBOT_UA = "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-User", "Claude-SearchBot",
           "anthropic-ai", "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended",
           "CCBot", "Meta-ExternalAgent", "Amazonbot", "Bytespider"]
SEARCH_BOTS = ["Googlebot", "Bingbot"]
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
CTX = ssl.create_default_context()

# ------------------------------------------------------------------ HTTP
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None
OPENER = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=CTX))

def raw_get(url, ua=UA, method="GET", timeout=25, accept="text/html,application/xhtml+xml,*/*;q=0.8"):
    """Single hop, no redirect following. Returns (status, headers dict lowercased, body bytes, ms)."""
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": ua, "Accept": accept, "Accept-Encoding": "gzip, deflate"})
    t = time.time()
    try:
        r = OPENER.open(req, timeout=timeout)
        st, hd, body = r.status, r.headers, r.read() if method == "GET" else b""
    except urllib.error.HTTPError as e:
        st, hd = e.code, e.headers
        try: body = e.read()
        except Exception: body = b""
    ms = int((time.time() - t) * 1000)
    h = {k.lower(): v for k, v in hd.items()}
    enc = h.get("content-encoding", "")
    try:
        if enc == "gzip": body = gzip.decompress(body)
        elif enc == "deflate": body = zlib.decompress(body)
    except Exception:
        pass
    # multi-valued headers we care about
    h["_link_all"] = hd.get_all("link") or []
    h["_xrobots_all"] = hd.get_all("x-robots-tag") or []
    return st, h, body, ms

def follow(url, ua=UA, max_hops=10, method="GET"):
    """Follow redirects by hand. Returns dict with chain [(url,status)], final url/status/headers/body."""
    chain, seen = [], set()
    cur = url
    for _ in range(max_hops + 1):
        try:
            st, h, body, ms = raw_get(cur, ua=ua, method=method)
        except Exception as e:
            chain.append((cur, "ERR:%s" % str(e)[:80]))
            return {"chain": chain, "final": cur, "status": "ERR", "error": str(e)[:200], "headers": {}, "body": b"", "ms": 0}
        chain.append((cur, st))
        if st in (301, 302, 303, 307, 308) and h.get("location"):
            nxt = urllib.parse.urljoin(cur, h["location"])
            if nxt in seen:
                chain.append((nxt, "LOOP"))
                return {"chain": chain, "final": nxt, "status": "LOOP", "headers": h, "body": b"", "ms": ms}
            seen.add(cur)
            cur = nxt
            continue
        return {"chain": chain, "final": cur, "status": st, "headers": h, "body": body, "ms": ms}
    return {"chain": chain, "final": cur, "status": "TOO_MANY", "headers": {}, "body": b"", "ms": 0}

# ------------------------------------------------------------------ HTML parse
class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles, self.metas, self.links_rel, self.anchors = [], [], [], []
        self.h = defaultdict(list); self.ld = []; self.imgs = []; self.scripts = []
        self.lang = None; self.base = None
        self._stack = []; self._cap = None; self._buf = []; self._a = None
        self._skip = 0; self.text = []; self.iframes = []; self.forms = 0
        self._in_ld = False; self._ld_buf = []
        self.noscript_depth = 0
        self.main_depth = 0; self.main_text = []; self.nav_depth = 0
    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if self._skip and tag in ("title", "h1", "h2", "h3", "a", "img", "meta", "link"):
            return  # inside <svg>/<template>: an svg <title> is not the page title
        if tag == "html": self.lang = a.get("lang")
        elif tag == "base": self.base = a.get("href")
        elif tag == "meta": self.metas.append(a)
        elif tag == "link": self.links_rel.append(a)
        elif tag == "title": self._cap = "title"; self._buf = []
        elif tag in ("h1", "h2", "h3"): self._cap = tag; self._buf = []
        elif tag == "a":
            self._a = {"href": a.get("href"), "rel": a.get("rel", ""), "text": []}
        elif tag == "img": self.imgs.append(a)
        elif tag == "iframe": self.iframes.append(a.get("src", ""))
        elif tag == "form": self.forms += 1
        elif tag == "script":
            if "ld+json" in a.get("type", ""):
                self._in_ld = True; self._ld_buf = []
            else:
                self.scripts.append(a)
                self._skip += 1
        elif tag in ("style", "svg", "template"): self._skip += 1
        elif tag == "noscript": self.noscript_depth += 1
        if tag == "main": self.main_depth += 1
        if tag in ("nav", "footer", "header"): self.nav_depth += 1
    def handle_endtag(self, tag):
        if tag == "main" and self.main_depth: self.main_depth -= 1
        if tag in ("nav", "footer", "header") and self.nav_depth: self.nav_depth -= 1
        if tag == "script":
            if self._in_ld:
                self.ld.append("".join(self._ld_buf)); self._in_ld = False
            elif self._skip: self._skip -= 1
        elif tag in ("style", "svg", "template") and self._skip: self._skip -= 1
        elif tag == "noscript" and self.noscript_depth: self.noscript_depth -= 1
        elif tag == self._cap:
            txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if tag == "title": self.titles.append(txt)
            else: self.h[tag].append(txt)
            self._cap = None
        elif tag == "a" and self._a is not None:
            self._a["text"] = re.sub(r"\s+", " ", "".join(self._a["text"])).strip()[:80]
            self.anchors.append(self._a); self._a = None
    def handle_data(self, d):
        if self._in_ld: self._ld_buf.append(d); return
        if self._skip: return
        if self._cap: self._buf.append(d)
        if self._a is not None: self._a["text"].append(d)
        if self.noscript_depth == 0:
            self.text.append(d)
            if self.nav_depth == 0: self.main_text.append(d)  # body minus nav/header/footer chrome

def shingles(txt, k=5, cap=3000):
    w = re.findall(r"[a-z0-9']+", txt.lower())
    return {hash(" ".join(w[i:i + k])) for i in range(0, max(0, len(w) - k + 1))} if len(w) >= k else set()

def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0

def meta(p, key, attr="name"):
    for m in p.metas:
        if m.get(attr, "").lower() == key:
            return m.get("content", "")
    return None

def json_types(obj, out=None):
    out = out if out is not None else []
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, list): out += [str(x) for x in t]
        elif t: out.append(str(t))
        for v in obj.values(): json_types(v, out)
    elif isinstance(obj, list):
        for v in obj: json_types(v, out)
    return out

def nodes(obj):
    """Flatten JSON-LD into typed nodes (handles @graph, arrays, nesting)."""
    if isinstance(obj, list):
        for x in obj: yield from nodes(x)
    elif isinstance(obj, dict):
        if "@type" in obj: yield obj
        for k, v in obj.items():
            if k != "@context": yield from nodes(v)

REQ = {  # rich-result required/recommended props (Google docs, 2026)
    "Organization": ["name", "url", "logo"],
    "WebSite": ["name", "url"],
    "BreadcrumbList": ["itemListElement"],
    "FAQPage": ["mainEntity"],
    "Article": ["headline", "datePublished", "author", "image"],
    "BlogPosting": ["headline", "datePublished", "author", "image"],
    "NewsArticle": ["headline", "datePublished", "author", "image"],
    "Service": ["name", "provider"],
    "SoftwareApplication": ["name", "offers", "applicationCategory"],
    "Product": ["name"],
    "Person": ["name"],
    "HowTo": ["name", "step"],
    "Event": ["name", "startDate", "location"],
}

def top_nodes(obj):
    """Top-level entities only (a block, an array item, or an @graph item). Nested
    nodes (publisher/author/provider) are references, not separate entities, so
    they must not count as duplicates or be held to rich-result requirements."""
    if isinstance(obj, list):
        for x in obj: yield from top_nodes(x)
    elif isinstance(obj, dict):
        if "@graph" in obj: yield from top_nodes(obj["@graph"])
        elif "@type" in obj: yield obj

def check_schema(blocks, visible_text, url):
    res = {"blocks": len(blocks), "malformed": [], "types": [], "problems": []}
    tcount = Counter()
    for i, raw in enumerate(blocks):
        raw = raw.strip()
        if not raw: continue
        try:
            obj = json.loads(raw)
        except Exception as e:
            res["malformed"].append("block %d: %s" % (i + 1, str(e)[:80])); continue
        for n in nodes(obj):
            t = n.get("@type"); res["types"].append(t[0] if isinstance(t, list) else t)
        for n in top_nodes(obj):
            t = n.get("@type"); t = t[0] if isinstance(t, list) else t
            tcount[t] += 1
            for prop in REQ.get(t, []):
                if prop not in n or n[prop] in ("", [], None):
                    res["problems"].append("%s missing %s" % (t, prop))
            if t in ("Article", "BlogPosting") and len(str(n.get("headline", ""))) > 110:
                res["problems"].append("%s headline >110 chars" % t)
            if t == "FAQPage":
                qs = [q for q in (n.get("mainEntity") or []) if isinstance(q, dict)]
                vt = re.sub(r"\s+", " ", visible_text.lower())
                missing = [q.get("name", "")[:60] for q in qs
                           if q.get("name") and re.sub(r"\s+", " ", q["name"].lower())[:50] not in vt]
                if missing:
                    res["problems"].append("FAQPage: %d/%d questions not in visible text (e.g. '%s')" % (len(missing), len(qs), missing[0]))
            if t == "BreadcrumbList":
                for it in n.get("itemListElement") or []:
                    if isinstance(it, dict) and "position" not in it:
                        res["problems"].append("BreadcrumbList item missing position"); break
            if t == "WebSite":
                pa = n.get("potentialAction")
                if pa: res["searchaction"] = json.dumps(pa)[:200]
    res["types"] = sorted(set(map(str, res["types"])))
    for t, c in tcount.items():
        if t in ("FAQPage", "BreadcrumbList", "Organization", "WebSite", "Service", "BlogPosting", "Article") and c > 1:
            res["problems"].append("duplicate %s x%d" % (t, c))
    return res

# ------------------------------------------------------------------ robots
def parse_robots(txt):
    groups, cur, last_ua = [], None, False
    sitemaps = []
    for line in txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line: continue
        k, v = [x.strip() for x in line.split(":", 1)]
        k = k.lower()
        if k == "sitemap": sitemaps.append(v); continue
        if k == "user-agent":
            if not last_ua:
                cur = {"agents": [], "rules": []}; groups.append(cur)
            cur["agents"].append(v.lower()); last_ua = True
        elif k in ("allow", "disallow") and cur is not None:
            cur["rules"].append((k, v)); last_ua = False
        else:
            last_ua = False
    return groups, sitemaps

def robots_allowed(groups, agent, path):
    agent = agent.lower()
    g = [x for x in groups if any(a != "*" and a in agent for a in x["agents"])]
    if not g: g = [x for x in groups if "*" in x["agents"]]
    rules = [r for x in g for r in x["rules"]]
    best, allow = -1, True
    for k, v in rules:
        if not v:
            continue
        pat = re.escape(v).replace(r"\*", ".*")
        if pat.endswith(r"\$"): pat = pat[:-2] + "$"
        if re.match(pat, path):
            if len(v) > best or (len(v) == best and k == "allow"):
                best, allow = len(v), (k == "allow")
    return allow, ("group:" + ",".join(g[0]["agents"]) if g else "no group")

# ------------------------------------------------------------------ issues
ISSUES = defaultdict(lambda: {"evidence": []})
def issue(rule, sev, title, evidence, fix, effort, owner="dev"):
    d = ISSUES[rule]
    d.update(rule=rule, severity=sev, title=title, fix=fix, effort=effort, owner=owner)
    if len(d["evidence"]) < 400:
        d["evidence"].append(evidence)

# ------------------------------------------------------------------ main crawl
def norm_url(u, host):
    p = urllib.parse.urlsplit(u)
    if p.scheme not in ("http", "https"): return None
    if p.netloc.lower() != host: return None
    path = p.path or "/"
    return urllib.parse.urlunsplit(("https", host, path, p.query, ""))

def audit_url(url, host, ua=UA):
    r = follow(url, ua=ua)
    rec = {"url": url, "status": r["status"], "final": r["final"],
           "chain": r["chain"], "ms": r.get("ms"), "error": r.get("error")}
    h = r["headers"]
    rec["headers"] = {k: h.get(k) for k in ("content-type", "cache-control", "x-robots-tag", "content-encoding",
                                           "strict-transport-security", "x-vercel-cache", "age", "content-length",
                                           "content-security-policy", "x-frame-options", "x-content-type-options",
                                           "referrer-policy", "permissions-policy", "link", "vary") if h.get(k)}
    rec["xrobots"] = h.get("_xrobots_all", [])
    body = r["body"]
    rec["bytes"] = len(body)
    ct = h.get("content-type", "")
    if r["status"] != 200 or "html" not in ct:
        return rec, []
    html = body.decode("utf-8", "ignore")
    p = Page()
    try:
        p.feed(html)
    except Exception as e:
        rec["parse_error"] = str(e)[:100]
    vis = re.sub(r"\s+", " ", " ".join(p.text)).strip()
    words = len(vis.split())
    canon = [l.get("href") for l in p.links_rel if "canonical" in l.get("rel", "").lower().split()]
    hreflang = [(l.get("hreflang"), l.get("href")) for l in p.links_rel if l.get("hreflang")]
    icons = [l.get("href") for l in p.links_rel if "icon" in l.get("rel", "").lower()]
    rec.update({
        "title": p.titles[0] if p.titles else None, "title_count": len(p.titles),
        "desc": meta(p, "description"), "robots": meta(p, "robots"), "googlebot": meta(p, "googlebot"),
        "viewport": meta(p, "viewport"), "lang": p.lang, "canonical": canon, "hreflang": hreflang,
        "h1": p.h["h1"], "h2_count": len(p.h["h2"]), "h2": p.h["h2"][:12], "words": words,
        "og": {k: meta(p, "og:" + k, "property") for k in ("title", "description", "image", "url", "type")},
        "twitter": {k: meta(p, "twitter:" + k) for k in ("card", "title", "image")},
        "icons": icons, "iframes": p.iframes[:10], "forms": p.forms,
        "text_hash": hashlib.md5(vis.lower().encode()).hexdigest(),
        "_shingles": shingles(" ".join(p.main_text)),
        "main_words": len(" ".join(p.main_text).split()),
        "text_sample": vis[:300],
    })
    # images
    rec["img_count"] = len(p.imgs)
    rec["img_no_alt"] = [i.get("src", "")[:120] for i in p.imgs if "alt" not in i][:10]
    rec["img_no_dims"] = sum(1 for i in p.imgs if not (i.get("width") and i.get("height")) and "fill" not in i.get("data-nimg", ""))
    rec["img_legacy_fmt"] = [i.get("src", "")[:120] for i in p.imgs
                             if re.search(r"\.(png|jpe?g|gif)(\?|$)", i.get("src", ""), re.I) and "/_next/image" not in i.get("src", "")][:10]
    # scripts / third parties
    srcs = [s.get("src") for s in p.scripts if s.get("src")]
    rec["scripts_ext"] = sorted({urllib.parse.urlsplit(urllib.parse.urljoin(url, s)).netloc for s in srcs} - {host, ""})
    rec["scripts_count"] = len(srcs)
    inline_js = sum(len(x) for x in re.findall(r"<script(?![^>]*ld\+json)[^>]*>(.*?)</script>", html, re.S))
    rec["inline_js_kb"] = inline_js // 1024
    rec["mixed_content"] = sorted(set(re.findall(r'(?:src|href)=["\'](http://[^"\']+)', html)))[:10]
    # schema
    rec["schema"] = check_schema(p.ld, vis, url)
    # links
    base = p.base or r["final"]
    links, ext = [], set()
    for a in p.anchors:
        href = (a["href"] or "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            if href.startswith("javascript:"): rec.setdefault("js_links", 0); rec["js_links"] += 1
            continue
        absu = urllib.parse.urljoin(base, href).split("#")[0]
        nu = norm_url(absu, host)
        if nu:
            links.append({"to": nu, "raw": href[:200], "anchor": a["text"], "nofollow": "nofollow" in a["rel"]})
        else:
            netloc = urllib.parse.urlsplit(absu).netloc
            if netloc: ext.add(netloc)
    rec["links_internal"] = len(links)
    rec["links_external_hosts"] = sorted(ext)[:40]
    rec["anchor_empty"] = sum(1 for l in links if not l["anchor"])
    return rec, links

def fetch_sitemaps(base, robots_sitemaps, checks):
    urls, meta_ = [], []
    todo = deque(robots_sitemaps or [base + "/sitemap.xml"])
    seen = set()
    while todo:
        sm = todo.popleft()
        if sm in seen: continue
        seen.add(sm)
        r = follow(sm)
        info = {"sitemap": sm, "status": r["status"], "chain": r["chain"],
                "content_type": r["headers"].get("content-type")}
        if r["status"] != 200:
            meta_.append(info); continue
        try:
            root = ET.fromstring(r["body"])
        except ET.ParseError as e:
            info["xml_error"] = str(e); meta_.append(info); continue
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        if root.tag.endswith("sitemapindex"):
            for loc in root.findall("s:sitemap/s:loc", ns):
                todo.append(loc.text.strip())
            info["type"] = "index"
        else:
            entries = root.findall("s:url", ns)
            info["type"] = "urlset"; info["count"] = len(entries)
            lm = Counter()
            for e in entries:
                loc = (e.findtext("s:loc", default="", namespaces=ns) or "").strip()
                last = e.findtext("s:lastmod", default=None, namespaces=ns)
                urls.append({"loc": loc, "lastmod": last})
                lm[last] += 1
            info["lastmod_top"] = lm.most_common(3)
            info["lastmod_missing"] = lm.get(None, 0)
            info["bytes"] = len(r["body"])
        meta_.append(info)
    checks["sitemaps"] = meta_
    return urls

def host_variants(host, sample_path, checks):
    apex = host[4:] if host.startswith("www.") else host
    www = "www." + apex
    out = {}
    for v in ["http://%s/" % apex, "https://%s/" % apex, "http://%s/" % www, "https://%s/" % www,
              "https://%s%s/" % (host, sample_path.rstrip("/")) if sample_path != "/" else None,
              "https://%s%s" % (host, sample_path.upper()) if sample_path != "/" else None,
              "https://%s/index.html" % host,
              "https://%s%s?utm_source=seo-audit&foo=bar" % (host, sample_path),
              "https://%s/%s" % (host, "".join(random.choice(string.ascii_lowercase) for _ in range(14)))]:
        if not v: continue
        r = follow(v)
        can = None
        if r["status"] == 200 and "html" in r["headers"].get("content-type", ""):
            m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', r["body"].decode("utf-8", "ignore"))
            can = m.group(1) if m else None
        out[v] = {"chain": r["chain"], "status": r["status"], "canonical": can,
                  "x_robots": r["headers"].get("_xrobots_all")}
    checks["host_variants"] = out
    return out

def infra(base, host, checks):
    out = {}
    try:
        cp = subprocess.run(["curl", "-sI", "--http2", "-o", "/dev/null", "-w", "%{http_version}", base + "/"],
                            capture_output=True, text=True, timeout=30)
        out["http_version"] = cp.stdout.strip()
    except Exception as e:
        out["http_version"] = "ERR %s" % e
    st, h, body, ms = raw_get(base + "/", accept="text/html")
    out["alt_svc"] = h.get("alt-svc")
    out["ttfb_ms_home"] = ms
    for enc in ("br", "gzip"):
        try:
            cp = subprocess.run(["curl", "-s", "-o", "/dev/null", "-D", "-", "-H", "Accept-Encoding: " + enc, base + "/"],
                                capture_output=True, text=True, timeout=30)
            m = re.search(r"(?im)^content-encoding:\s*(\S+)", cp.stdout)
            out["encoding_" + enc] = m.group(1) if m else None
        except Exception:
            pass
    out["security_headers"] = {k: h.get(k) for k in ("strict-transport-security", "content-security-policy",
                               "x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy")}
    out["html_cache_control"] = h.get("cache-control")
    # a static asset
    m = re.search(r'(/_next/static/[^"\']+\.js)', body.decode("utf-8", "ignore"))
    if m:
        st2, h2, _, _ = raw_get(base + m.group(1), method="HEAD")
        out["static_asset"] = {"url": m.group(1), "status": st2, "cache-control": h2.get("cache-control")}
    checks["infra"] = out
    return out

def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__); sys.exit(1)
    base = a[0].rstrip("/")
    if not base.startswith("http"): base = "https://" + base
    host = urllib.parse.urlsplit(base).netloc.lower()
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    out = opt("--out", "techaudit-out"); os.makedirs(out, exist_ok=True)
    MAX = int(opt("--max", 1500)); W = int(opt("--workers", 8))
    THIN = int(opt("--thin", 250)); DEPTH_LIMIT = int(opt("--depth-limit", 4))
    previews = [a[i + 1] for i, x in enumerate(a) if x == "--preview-host"]
    probes = [a[i + 1] for i, x in enumerate(a) if x == "--probe"]
    checks = {"base": base, "host": host, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    log = lambda *m: sys.stderr.write(" ".join(str(x) for x in m) + "\n")

    # ---- robots
    st, h, body, _ = raw_get(base + "/robots.txt", accept="text/plain")
    rtxt = body.decode("utf-8", "ignore") if st == 200 else ""
    groups, rsm = parse_robots(rtxt)
    checks["robots"] = {"status": st, "content_type": h.get("content-type"), "sitemaps": rsm, "bytes": len(body)}
    if st != 200:
        issue("robots-missing", "high", "robots.txt not returning 200", "%s/robots.txt -> %s" % (base, st),
              "Serve a robots.txt with Sitemap: line", "S")
    if not rsm:
        issue("robots-no-sitemap", "low", "robots.txt does not declare the sitemap", base + "/robots.txt",
              "Add 'Sitemap: %s/sitemap.xml'" % base, "S")
    ai = {}
    for bot in AI_BOTS + SEARCH_BOTS:
        ok, grp = robots_allowed(groups, bot, "/")
        ai[bot] = {"allowed_root": ok, "group": grp}
        if not ok:
            issue("robots-bot-blocked", "high" if bot in SEARCH_BOTS else "medium",
                  "robots.txt blocks a search/AI crawler from /", "%s blocked (%s)" % (bot, grp),
                  "Allow the bot unless blocking is a deliberate policy decision", "S", "owner")
        explicit = any(bot.lower() in g["agents"] for g in groups)
        ai[bot]["explicit_group"] = explicit
    checks["ai_crawlers"] = ai
    missing_explicit = [b for b in AI_BOTS if not ai[b]["explicit_group"]]
    if missing_explicit:
        issue("robots-ai-implicit", "info", "AI crawlers covered only by the * group (fine, but not explicit)",
              ", ".join(missing_explicit), "Optional: add explicit groups so policy is intentional and visible", "S", "seo")
    # llms.txt
    llms = {}
    for pth in ("/llms.txt", "/llms-full.txt"):
        s2, h2, b2, _ = raw_get(base + pth, accept="text/plain")
        llms[pth] = {"status": s2, "bytes": len(b2), "content_type": h2.get("content-type"),
                     "x_robots": h2.get("_xrobots_all")}
    checks["llms"] = llms
    if llms["/llms.txt"]["status"] != 200:
        issue("llms-missing", "low", "No /llms.txt", base + "/llms.txt -> %s" % llms["/llms.txt"]["status"],
              "Publish an llms.txt index of key pages (cheap, helps AI answer engines)", "S", "seo")

    # ---- real bot UAs (WAF / bot-protection can 403 crawlers robots.txt welcomes)
    bot_uas = {"Googlebot": GOOGLEBOT_UA,
               "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
               "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
               "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)"}
    ua_access = {}
    for name, ua in bot_uas.items():
        r = follow(base + "/", ua=ua)
        ua_access[name] = {"status": r["status"], "bytes": len(r["body"])}
        if r["status"] != 200:
            issue("bot-ua-blocked", "critical" if name == "Googlebot" else "high",
                  "Crawler user-agent is blocked at the edge (WAF/bot protection)", "%s -> %s" % (name, r["status"]),
                  "Allow-list verified bots in the firewall / bot-protection settings", "S")
    checks["bot_ua_access"] = ua_access

    # ---- sitemaps
    sm_entries = fetch_sitemaps(base, rsm, checks)
    sm_urls = []
    for e in sm_entries:
        nu = norm_url(e["loc"], host)
        if not nu:
            issue("sitemap-offhost", "medium", "Sitemap lists URLs on another host/scheme", e["loc"],
                  "Sitemap must list only canonical https://%s URLs" % host, "S")
            continue
        sm_urls.append(nu)
    dupes = [u for u, c in Counter(sm_urls).items() if c > 1]
    for u in dupes[:20]:
        issue("sitemap-duplicate", "low", "Duplicate URL in sitemap", u, "Dedupe sitemap generation", "S")
    sm_set = set(sm_urls)
    lm = Counter(e["lastmod"] for e in sm_entries)
    if sm_entries:
        top, n = lm.most_common(1)[0]
        if top and n / len(sm_entries) > 0.4:
            issue("sitemap-lastmod-static", "medium", "Sitemap lastmod is a hard-coded date for most URLs",
                  "%d/%d URLs share lastmod %s" % (n, len(sm_entries), top),
                  "Emit real per-page modified dates (CMS _updatedAt, git mtime) or omit lastmod; Google ignores lastmod it learns is unreliable",
                  "M")
        future = [e for e in sm_entries if e["lastmod"] and e["lastmod"][:10] > time.strftime("%Y-%m-%d")]
        for e in future[:10]:
            issue("sitemap-lastmod-future", "low", "Sitemap lastmod in the future", "%s %s" % (e["loc"], e["lastmod"]), "Fix date source", "S")
    for s in checks["sitemaps"]:
        if s.get("xml_error") or s["status"] != 200:
            issue("sitemap-broken", "critical", "Sitemap unreachable or invalid XML",
                  "%s -> %s %s" % (s["sitemap"], s["status"], s.get("xml_error", "")), "Fix sitemap route", "S")

    # ---- crawl (BFS from home + sitemap seeds)
    home = base + "/"
    depth = {norm_url(home, host): 0}
    queue = deque([norm_url(home, host)])
    for u in sm_urls:
        if u not in depth:
            queue.append(u)
    queued = set(queue)
    pages, edges = {}, []
    inlinks = defaultdict(set)
    pf = open(os.path.join(out, "pages.jsonl"), "w")
    param_seen = defaultdict(int)
    t0 = time.time()
    with ThreadPoolExecutor(W) as ex:
        futs = {}
        while queue or futs:
            while queue and len(futs) < W * 2 and len(pages) + len(futs) < MAX:
                u = queue.popleft()
                futs[ex.submit(audit_url, u, host)] = u
            if not futs: break
            done = next(as_completed(futs))
            u = futs.pop(done)
            try:
                rec, links = done.result()
            except Exception as e:
                rec, links = {"url": u, "status": "ERR", "error": str(e)[:200], "chain": []}, []
            rec["in_sitemap"] = u in sm_set
            pages[u] = rec
            pf.write(json.dumps({k: v for k, v in rec.items() if k != "_shingles"}) + "\n"); pf.flush()
            for l in links:
                edges.append((u, l["to"], l["anchor"], l["nofollow"]))
                inlinks[l["to"]].add(u)
                tgt = l["to"]
                if "?" in tgt:
                    key = tgt.split("?")[0]
                    param_seen[key] += 1
                    if param_seen[key] > 2:  # don't explode on faceted params
                        continue
                if tgt not in queued and not re.search(r"\.(png|jpe?g|gif|webp|avif|svg|pdf|zip|mp4|webm|ico|css|js|xml|txt|json|md)(\?|$)", tgt, re.I):
                    queued.add(tgt); queue.append(tgt)
            if len(pages) % 50 == 0:
                log("crawled %d (queue %d) %.0fs" % (len(pages), len(queue), time.time() - t0))
    pf.close()
    if queue:
        checks["crawl_truncated"] = len(queue)
        issue("crawl-cap", "info", "Crawl hit --max before the queue emptied", "%d URLs unvisited" % len(queue),
              "Re-run with a higher --max", "S", "seo")
    with open(os.path.join(out, "edges.tsv"), "w") as f:
        for s, d, an, nf in edges:
            f.write("%s\t%s\t%s\t%s\n" % (s, d, an.replace("\t", " "), int(nf)))

    # ---- depth via BFS on follow links
    adj = defaultdict(set)
    for s, d, an, nf in edges:
        if not nf: adj[s].add(d)
    dq = deque([norm_url(home, host)]); depth = {norm_url(home, host): 0}
    while dq:
        x = dq.popleft()
        tgt = pages.get(x, {}).get("final")
        srcs = [x] + ([tgt] if tgt and tgt != x else [])
        for s in srcs:
            for y in adj.get(s, ()):
                if y not in depth:
                    depth[y] = depth[x] + 1; dq.append(y)
    for u, rec in pages.items():
        rec["depth"] = depth.get(u)
        rec["inlinks"] = len(inlinks.get(u, set()) - {u})

    # ---- per-page issues
    titles, descs, hashes = defaultdict(list), defaultdict(list), defaultdict(list)
    for u, r in pages.items():
        st = r["status"]; chain = r.get("chain") or []
        linked_from = sorted(inlinks.get(u, ()))[:3]
        src = (" <- linked from %s" % linked_from[0]) if linked_from else ""
        if st in ("ERR", "LOOP", "TOO_MANY"):
            issue("fetch-error", "high", "URL errors / loops / too many redirects", "%s %s %s%s" % (u, st, r.get("error", ""), src),
                  "Fix the route or remove links to it", "S")
            continue
        if len(chain) > 1:
            hops = len(chain) - 1
            if u in sm_set:
                issue("sitemap-redirect", "high", "Sitemap lists a URL that redirects",
                      "%s -> %s (%s)" % (u, r["final"], chain[0][1]), "List the final canonical URL in the sitemap", "S")
            if inlinks.get(u):
                issue("internal-redirect", "medium", "Internal links point at redirecting URLs",
                      "%s -> %s%s" % (u, r["final"], src), "Update hrefs to the final URL (saves a hop per crawl/click)", "S")
            if hops > 1:
                issue("redirect-chain", "medium", "Redirect chain (>1 hop)", " -> ".join("%s[%s]" % c for c in chain),
                      "Collapse to a single 301", "S")
            if chain[0][1] in (302, 307) and inlinks.get(u):
                issue("redirect-temporary", "low", "Temporary (302/307) redirect on an internally linked URL",
                      "%s %s -> %s" % (u, chain[0][1], r["final"]), "Use 301/308 for permanent moves", "S")
        if isinstance(st, int) and st >= 500:
            issue("http-5xx", "critical", "Server error (5xx)", "%s -> %s%s" % (u, st, src), "Fix the route; 5xx at scale throttles crawling", "M")
            continue
        if isinstance(st, int) and 400 <= st < 500:
            sev = "high" if (u in sm_set or inlinks.get(u)) else "low"
            issue("http-4xx", sev, "Broken URL (4xx) linked internally or in sitemap", "%s -> %s%s%s" % (u, st, src, " [in sitemap]" if u in sm_set else ""),
                  "Fix or remove the link / sitemap entry; 301 if the content moved", "S")
            continue
        if st != 200 or "title" not in r:
            continue
        # indexability
        rob = " ".join(filter(None, [r.get("robots"), r.get("googlebot")] + r.get("xrobots", []))).lower()
        noindex = "noindex" in rob
        r["noindex"] = noindex
        can = r.get("canonical") or []
        canon_abs = urllib.parse.urljoin(r["final"], can[0]) if can else None
        r["canonical_abs"] = canon_abs
        if len(set(can)) > 1:
            issue("canonical-multiple", "high", "Multiple conflicting canonical tags", "%s %s" % (u, can), "Emit exactly one canonical", "S")
        if not can and not noindex:
            issue("canonical-missing", "medium", "Indexable page without a canonical", u, "Add a self-referencing canonical", "S")
        canon_other = False
        if canon_abs:
            n1 = canon_abs.rstrip("/"); n2 = r["final"].split("?")[0].rstrip("/")
            if n1 != n2:
                canon_other = True
                chost = urllib.parse.urlsplit(canon_abs).netloc
                if chost and chost != host:
                    issue("canonical-crossdomain", "high", "Canonical points to another host", "%s -> %s" % (u, canon_abs),
                          "Point canonical at the https://%s version unless syndication is intended" % host, "S")
                elif "?" not in u:
                    issue("canonical-elsewhere", "medium" if u in sm_set else "low", "Page canonicalises to a different URL",
                          "%s -> %s%s" % (u, canon_abs, " [in sitemap]" if u in sm_set else ""),
                          "Either make it self-canonical or drop it from sitemap/internal links", "S")
                ctgt = pages.get(norm_url(canon_abs, host) or "")
                if ctgt and ctgt.get("status") != 200:
                    issue("canonical-broken", "high", "Canonical target is not a 200", "%s -> %s (%s)" % (u, canon_abs, ctgt.get("status")),
                          "Canonical must resolve 200 directly", "S")
        r["indexable"] = not noindex and not canon_other
        if noindex and u in sm_set:
            issue("sitemap-noindex", "high", "Sitemap lists a noindex URL", "%s (%s)" % (u, rob), "Drop noindex URLs from the sitemap (conflicting signals)", "S")
        if noindex and inlinks.get(u) and len(inlinks[u]) >= 5:
            issue("noindex-linked", "low", "Heavily linked page is noindex (check intent)", "%s (%d inlinks)" % (u, len(inlinks[u])),
                  "Confirm noindex is deliberate", "S", "seo")
        if r["indexable"] and u not in sm_set and "?" not in u:
            issue("sitemap-missing", "medium", "Indexable 200 page missing from sitemap", u + src,
                  "Add to sitemap generator (or noindex if it should not rank)", "S")
        if r["indexable"] and u in sm_set and not (inlinks.get(u, set()) - {u}):
            issue("orphan", "high", "Orphan: in sitemap, no internal links found", u,
                  "Link from a relevant hub/nav/footer/related-posts block", "S", "seo")
        if r["indexable"] and r.get("depth") is not None and r["depth"] > DEPTH_LIMIT:
            issue("deep-page", "low", "Indexable page is >%d clicks from home" % DEPTH_LIMIT, "%s depth %d" % (u, r["depth"]),
                  "Surface via hubs/breadcrumbs/related links", "M", "seo")
        if r["indexable"] and r.get("depth") is None and u in sm_set and inlinks.get(u):
            issue("unreachable-from-home", "medium", "Not reachable from the homepage by followed links", u,
                  "Link it from a crawlable hub", "S", "seo")
        # soft 404
        ttl = (r.get("title") or "").lower(); h1 = " ".join(r.get("h1") or []).lower()
        if re.search(r"\b(404|not found|page not found|doesn.t exist)\b", ttl + " " + h1) or (r["words"] < 60 and not noindex):
            issue("soft-404", "high", "Soft 404: 200 status but error/empty content", "%s title='%s' words=%d" % (u, r.get("title"), r["words"]),
                  "Return a real 404/410 or add content", "S")
        # head/meta
        t = r.get("title") or ""
        if not t:
            issue("title-missing", "high", "Missing <title>", u, "Add a unique title", "S", "seo")
        else:
            if r["indexable"]: titles[t].append(u)
            if len(t) > 65:
                issue("title-long", "low", "Title >65 chars (truncates in SERP)", "%s (%d) %s" % (u, len(t), t[:90]), "Tighten to ~50-60 chars, keyword first", "S", "seo")
            if len(t) < 25:
                issue("title-short", "low", "Title <25 chars", "%s '%s'" % (u, t), "Add the primary keyword + qualifier", "S", "seo")
        if r.get("title_count", 0) > 1:
            issue("title-multiple", "medium", "Multiple <title> tags", "%s (%d)" % (u, r["title_count"]), "Emit one title (check layout + page metadata)", "S")
        d = r.get("desc") or ""
        if not d:
            if r["indexable"]:
                issue("desc-missing", "medium", "Missing meta description", u, "Write a 140-155 char intent-matched description", "S", "seo")
        else:
            if r["indexable"]: descs[d].append(u)
            if len(d) > 165:
                issue("desc-long", "low", "Meta description >165 chars", "%s (%d)" % (u, len(d)), "Trim to ~150", "S", "seo")
            if len(d) < 70:
                issue("desc-short", "low", "Meta description <70 chars", "%s (%d) '%s'" % (u, len(d), d), "Expand with benefit + CTA", "S", "seo")
        if not r.get("h1"):
            issue("h1-missing", "medium", "No <h1> in server HTML", u, "Give each page one descriptive H1", "S")
        elif len(r["h1"]) > 1:
            issue("h1-multiple", "low", "Multiple <h1>", "%s %s" % (u, [x[:40] for x in r["h1"][:3]]), "Demote secondary H1s to H2", "S")
        if not r.get("lang"):
            issue("lang-missing", "low", "<html> missing lang", u, "Set lang='en'", "S")
        if not r.get("viewport"):
            issue("viewport-missing", "high", "No meta viewport (mobile-first indexing)", u, "Add viewport meta", "S")
        og = r.get("og") or {}
        if not og.get("image") or not og.get("title"):
            issue("og-missing", "low", "Missing og:title/og:image (poor link previews)", "%s og:image=%s" % (u, og.get("image")), "Add OG tags / default OG image", "S")
        if not (r.get("twitter") or {}).get("card"):
            issue("twitter-missing", "low", "Missing twitter:card", u, "Add twitter:card=summary_large_image", "S")
        if r["indexable"] and r["words"] < THIN:
            issue("thin", "medium", "Thin indexable page (<%d words in server HTML)" % THIN, "%s (%d words)" % (u, r["words"]),
                  "Expand with specific, first-hand content or noindex/consolidate", "M", "content")
        if r["indexable"]: hashes[r["text_hash"]].append(u)
        if r.get("mixed_content"):
            issue("mixed-content", "medium", "http:// resources/links on an https page", "%s %s" % (u, r["mixed_content"][:2]), "Switch to https URLs", "S")
        if r.get("img_no_alt"):
            issue("img-alt", "low", "Images without alt attribute", "%s e.g. %s" % (u, r["img_no_alt"][0]), "Add descriptive alt (or alt='' for decorative)", "S")
        if r.get("img_legacy_fmt"):
            issue("img-format", "low", "Unoptimised PNG/JPG/GIF served directly (not via next/image)", "%s e.g. %s" % (u, r["img_legacy_fmt"][0]),
                  "Serve via next/image or pre-convert to AVIF/WebP", "S")
        if r.get("hreflang"):
            codes = [x[0] for x in r["hreflang"]]
            if "x-default" not in codes:
                issue("hreflang-xdefault", "low", "hreflang without x-default", u, "Add x-default", "S")
        # schema
        sc = r.get("schema") or {}
        for m in sc.get("malformed", []):
            issue("schema-malformed", "high", "Malformed JSON-LD (Google drops it)", "%s %s" % (u, m), "Fix the JSON serialisation", "S")
        for pb in sc.get("problems", []):
            sev = "medium" if ("not in visible" in pb or "duplicate" in pb) else "low"
            issue("schema-" + re.sub(r"[^a-z]+", "-", pb.split(":")[0].lower())[:40].strip("-"), sev,
                  "Structured data: " + re.sub(r"\(e\.g\..*", "", re.sub(r"\d+/\d+", "N", pb)).strip(), "%s: %s" % (u, pb),
                  "Emit only schema that describes visible content; fill required props", "S")
        if sc.get("searchaction"):
            checks.setdefault("searchaction", sc["searchaction"])
        # cache
        cc = (r.get("headers") or {}).get("cache-control", "")
        if "no-store" in cc or "private" in cc:
            issue("html-nocache", "low", "HTML served uncacheable (slower TTFB for bots/users)", "%s cache-control=%s" % (u, cc),
                  "Use ISR/static where possible", "M")
        if r.get("ms") and r["ms"] > 1500:
            issue("slow-ttfb", "medium", "Slow response (>1.5s from crawler, uncached?)", "%s %dms (x-vercel-cache=%s)" % (u, r["ms"], (r.get("headers") or {}).get("x-vercel-cache")),
                  "Make the route static/ISR; check data fetching on the server", "M")
    for t, us in titles.items():
        if len(us) > 1:
            issue("title-duplicate", "medium", "Duplicate titles across indexable pages", "'%s' x%d: %s" % (t[:70], len(us), ", ".join(us[:4])),
                  "Make titles unique per intent", "S", "seo")
    for d, us in descs.items():
        if len(us) > 1:
            issue("desc-duplicate", "low", "Duplicate meta descriptions", "'%s' x%d: %s" % (d[:60], len(us), ", ".join(us[:4])), "Unique descriptions", "S", "seo")
    # near-duplicates within a section (same first path segment), main content only
    groups_ = defaultdict(list)
    for u, r in pages.items():
        if r.get("indexable") and r.get("_shingles"):
            groups_[urllib.parse.urlsplit(u).path.strip("/").split("/")[0]].append(u)
    near = {}
    for g, us in groups_.items():
        sims = []
        for i in range(len(us)):
            for j in range(i + 1, len(us)):
                jv = jaccard(pages[us[i]]["_shingles"], pages[us[j]]["_shingles"])
                sims.append(jv)
                if jv >= 0.6:
                    issue("near-duplicate", "high" if jv >= 0.8 else "medium",
                          "Near-duplicate main content (5-gram Jaccard, nav/footer excluded)",
                          "%.2f %s ~ %s" % (jv, us[i], us[j]),
                          "Differentiate (unique examples, data, workflows) or consolidate + 301/canonical", "M", "content")
        if sims:
            near[g] = {"pages": len(us), "pairs": len(sims), "mean": round(sum(sims) / len(sims), 3), "max": round(max(sims), 3),
                       "pairs_ge_0.5": sum(1 for x in sims if x >= 0.5)}
    checks["near_dup_by_section"] = near
    for r in pages.values():
        r.pop("_shingles", None)
    for hsh, us in hashes.items():
        if len(us) > 1:
            issue("duplicate-content", "high", "Exact-duplicate body text on multiple indexable URLs", "x%d: %s" % (len(us), ", ".join(us[:5])),
                  "Canonicalise/redirect duplicates to one URL", "S")
    # sitemap URLs not crawled 200
    for u in sm_urls:
        if u not in pages:
            continue

    # ---- host variants / infra / previews / probes
    sample = next((urllib.parse.urlsplit(u).path for u in sm_urls if urllib.parse.urlsplit(u).path.count("/") == 1 and len(urllib.parse.urlsplit(u).path) > 1), "/about")
    hv = host_variants(host, sample, checks)
    for v, info in hv.items():
        ch = info["chain"]
        if v.startswith("http://") or urllib.parse.urlsplit(v).netloc != host:
            if info["status"] != 200 or not str(info["chain"][-1][0]).startswith("https://%s/" % host):
                issue("host-consolidation", "high", "Host/scheme variant does not land on https://%s" % host, " -> ".join("%s[%s]" % c for c in ch), "301 every variant to the canonical host in one hop", "S")
            elif len(ch) > 2:
                issue("host-variant-chain", "low", "Host/scheme variant takes >1 hop", " -> ".join("%s[%s]" % c for c in ch), "Single 301 straight to https://%s" % host, "S")
        elif v.endswith("/") and sample.rstrip("/") in v and v != "https://%s/" % host:
            if info["status"] == 200 and len(ch) == 1:
                can = info.get("canonical") or ""
                issue("trailing-slash", "medium" if can.rstrip("/") != v.rstrip("/") or not can else "low",
                      "Trailing-slash variant serves 200 (duplicate URL)", "%s 200 canonical=%s" % (v, can), "301 to the non-slash form (Next.js trailingSlash default)", "S")
        elif v.endswith(sample.upper()) and info["status"] == 200:
            issue("case-duplicate", "low", "Uppercase path variant returns 200", v, "Redirect or 404 case variants", "S")
        elif "utm_source" in v and info["status"] == 200:
            can = info.get("canonical") or ""
            if "utm_source" in can or not can:
                issue("param-canonical", "high", "Parameter URL is self-canonical (tracking params create duplicates)", "%s canonical=%s" % (v, can), "Canonical must strip query params", "S")
        elif "index.html" in v and info["status"] == 200:
            issue("index-html", "low", "/index.html serves 200", v, "301 to /", "S")
        elif info["status"] == 200 and v.rsplit("/", 1)[-1].isalpha() and len(v.rsplit("/", 1)[-1]) == 14:
            issue("soft-404-random", "critical", "Random nonexistent URL returns 200 (site-wide soft 404)", v, "Return 404 for unknown routes", "S")
    # ---- WebSite SearchAction must point at a working search
    sa_txt = checks.get("searchaction")
    if sa_txt:
        m = re.search(r'"(?:urlTemplate|target)":\s*"([^"]*\{search_term_string\}[^"]*)"', sa_txt)
        if m:
            tpl = m.group(1)
            r1 = follow(tpl.replace("{search_term_string}", "zzqxnomatch%d" % random.randint(1000, 9999)))
            r0 = follow(tpl.split("?")[0])
            same = hashlib.md5(re.sub(rb"\s+", b"", r1["body"])).hexdigest() == hashlib.md5(re.sub(rb"\s+", b"", r0["body"])).hexdigest()
            checks["searchaction_test"] = {"template": tpl, "query_status": r1["status"], "identical_to_unfiltered": same}
            if r1["status"] != 200 or same:
                issue("searchaction-broken", "medium", "WebSite SearchAction advertises a search that does not filter",
                      "%s returns %s, byte-identical to the unfiltered page: %s" % (tpl, r1["status"], same),
                      "Remove potentialAction.SearchAction or implement real ?q= filtering", "S")
    inf = infra(base, host, checks)
    sh = inf["security_headers"]
    if not sh.get("strict-transport-security"):
        issue("hsts", "medium", "No HSTS header", base, "Add Strict-Transport-Security", "S")
    if not sh.get("content-security-policy"):
        issue("csp", "low", "No Content-Security-Policy", base, "Add a CSP (report-only first)", "M")
    if not sh.get("permissions-policy"):
        issue("permissions-policy", "low", "No Permissions-Policy header", base, "Add a restrictive Permissions-Policy", "S")
    if not (inf.get("encoding_br") or inf.get("encoding_gzip")):
        issue("compression", "high", "HTML not compressed", base, "Enable br/gzip", "S")
    if inf.get("http_version") not in ("2", "3"):
        issue("http-version", "low", "Not served over HTTP/2+", "%s %s" % (base, inf.get("http_version")), "Enable HTTP/2", "S")
    if not inf.get("alt_svc"):
        issue("http3", "info", "No HTTP/3 advertised (alt-svc)", base, "Optional; Vercel/Cloudflare can enable", "S")
    sa = inf.get("static_asset") or {}
    if sa and "immutable" not in (sa.get("cache-control") or "") and "max-age=31536000" not in (sa.get("cache-control") or ""):
        issue("static-cache", "medium", "Hashed static assets not long-cached", "%s %s" % (sa.get("url"), sa.get("cache-control")), "Cache-Control: public, max-age=31536000, immutable", "S")
    prev = {}
    if "--preview-from-gh" in a:
        repo = opt("--preview-from-gh")
        try:
            ids = subprocess.run(["gh", "api", "repos/%s/deployments?per_page=6" % repo, "--jq", ".[].id"],
                                 capture_output=True, text=True, timeout=60).stdout.split()
            for i in ids:
                u = subprocess.run(["gh", "api", "repos/%s/deployments/%s/statuses" % (repo, i), "--jq", ".[0].environment_url"],
                                   capture_output=True, text=True, timeout=60).stdout.strip()
                if u.startswith("http"): previews.append(urllib.parse.urlsplit(u).netloc)
        except Exception as e:
            checks["preview_discovery_error"] = str(e)[:200]
    for ph in sorted(set(previews)):
        try:
            st0, h0, _, _ = raw_get("https://%s/" % ph)
        except Exception as e:
            prev[ph] = {"error": str(e)[:120]}; continue
        xr0 = " ".join(h0.get("_xrobots_all") or []).lower()
        if "noindex" in xr0 or (st0 in (301, 302, 307, 308) and "vercel.com/sso" in (h0.get("location") or "")) or st0 in (401, 403):
            prev[ph] = {"status": st0, "x_robots": xr0, "protected": True}
            continue
        r = follow("https://%s/" % ph)
        xr = " ".join(r["headers"].get("_xrobots_all") or []).lower()
        mrob = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', r["body"].decode("utf-8", "ignore"), re.I)
        can = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', r["body"].decode("utf-8", "ignore"))
        prev[ph] = {"chain": r["chain"], "status": r["status"], "x_robots": xr, "meta_robots": mrob.group(1) if mrob else None,
                    "canonical": can.group(1) if can else None}
        ttl = re.search(r"<title>([^<]*)", r["body"].decode("utf-8", "ignore"))
        prev[ph]["title"] = ttl.group(1)[:80] if ttl else None
        if r["status"] == 200 and "noindex" not in xr and not (mrob and "noindex" in mrob.group(1).lower()):
            sev = "high" if not (can and host in can.group(1)) else "medium"
            issue("preview-indexable", sev, "Preview/staging host is indexable", "%s 200, no noindex, canonical=%s, title=%s" % (ph, can.group(1) if can else None, prev[ph]["title"]),
                  "VERIFY the host is yours (check title; a look-alike *.vercel.app may be someone else). If so: send X-Robots-Tag: noindex on non-production hosts (middleware on VERCEL_ENV!=production) or protect previews", "S")
    checks["previews"] = prev
    pr = {}
    for pth in probes:
        r = follow(base + pth)
        body = r["body"][:300].decode("utf-8", "ignore")
        pr[pth] = {"status": r["status"], "chain": r["chain"], "content_type": r["headers"].get("content-type"),
                   "x_robots": r["headers"].get("_xrobots_all"), "snippet": body[:160]}
    checks["probes"] = pr
    checks["searchaction"] = checks.get("searchaction")
    checks["stats"] = {
        "crawled": len(pages), "sitemap_urls": len(sm_urls), "status": Counter(str(p["status"]) for p in pages.values()),
        "indexable": sum(1 for p in pages.values() if p.get("indexable")),
        "noindex": sum(1 for p in pages.values() if p.get("noindex")),
        "depth_hist": Counter(str(p.get("depth")) for p in pages.values() if p.get("indexable")),
        "edges": len(edges), "seconds": int(time.time() - t0)}
    json.dump(checks, open(os.path.join(out, "site-checks.json"), "w"), indent=1, default=str)
    # rewrite pages with derived fields
    with open(os.path.join(out, "pages.jsonl"), "w") as f:
        for r in pages.values():
            f.write(json.dumps(r, default=str) + "\n")
    iss = sorted(ISSUES.values(), key=lambda d: (SEV_ORDER[d["severity"]], -len(d["evidence"])))
    for d in iss:
        d["count"] = len(d["evidence"])
    json.dump(iss, open(os.path.join(out, "issues.json"), "w"), indent=1)
    L = ["# Technical audit: %s (%s)" % (host, checks["started"]), "",
         "Crawled %(crawled)d URLs (%(sitemap_urls)d in sitemap), %(indexable)d indexable, %(noindex)d noindex, %(edges)d internal links, %(seconds)ds." % checks["stats"], "",
         "| severity | rule | issue | count | example evidence | fix | effort | owner |", "|---|---|---|---|---|---|---|---|"]
    for d in iss:
        L.append("| %s | %s | %s | %d | %s | %s | %s | %s |" % (d["severity"], d["rule"], d["title"], d["count"],
                 d["evidence"][0].replace("|", "/")[:160], d["fix"], d["effort"], d["owner"]))
    open(os.path.join(out, "issues.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
