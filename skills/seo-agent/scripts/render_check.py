#!/usr/bin/env python3
"""Rendering check for the seo-agent skill: raw HTML vs JS-rendered DOM.

Answers "what does Googlebot see before and after JavaScript?" per URL.
Fetches the raw server HTML (as Googlebot smartphone UA) and the rendered DOM
(headless Chrome --dump-dom, same UA), then diffs the SEO-critical parts:
title, meta description, canonical, meta robots, H1s, word count, internal
links and JSON-LD blocks. Content or links that exist ONLY after rendering are
JS-dependent: Google usually renders them, but late, and most AI crawlers
(GPTBot, ClaudeBot, PerplexityBot) do not run JS at all.

Usage:
  python3 render_check.py --out DIR <url> [<url> ...]
Writes DIR/render-<slug>.json and DIR/render.md. Needs Google Chrome/Chromium
($CHROME_PATH or the default macOS/Linux locations).
Severity guide printed per URL:
  critical  rendered DOM changes robots/canonical, or raw HTML has no H1/body text
  high      >30% of words or >20% of internal links only appear after JS
  medium    title/description differ raw vs rendered, or JSON-LD only after JS
  ok        otherwise
"""
import sys, os, re, json, subprocess, urllib.request, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from techaudit import Page, meta
import techaudit as T

CHROMES = [os.environ.get("CHROME_PATH", ""),
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
           "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]

def rendered(url, ua):
    chrome = next((c for c in CHROMES if c and os.path.exists(c)), None)
    if not chrome:
        raise RuntimeError("Chrome not found; set CHROME_PATH")
    cp = subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                         "--user-agent=" + ua, "--virtual-time-budget=15000", "--window-size=412,915",
                         "--dump-dom", url], capture_output=True, timeout=90)
    return cp.stdout.decode("utf-8", "ignore")

def extract(html, url, host):
    p = Page(); p.feed(html)
    vis = re.sub(r"\s+", " ", " ".join(p.text)).strip()
    links = set()
    for a in p.anchors:
        href = (a["href"] or "").strip()
        if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
            nu = T.norm_url(T.urllib.parse.urljoin(url, href).split("#")[0], host)
            if nu: links.add(nu)
    canon = [l.get("href") for l in p.links_rel if "canonical" in l.get("rel", "").lower().split()]
    return {"title": p.titles[0] if p.titles else None, "desc": meta(p, "description"),
            "robots": meta(p, "robots"), "canonical": canon, "h1": p.h["h1"],
            "words": len(vis.split()), "links": sorted(links), "ld_blocks": len([x for x in p.ld if x.strip()]),
            "text": vis}

def check(url, out):
    host = T.urllib.parse.urlsplit(url).netloc.lower()
    r = T.follow(url, ua=T.GOOGLEBOT_UA)
    raw = extract(r["body"].decode("utf-8", "ignore"), r["final"], host)
    ren = extract(rendered(r["final"], T.GOOGLEBOT_UA), r["final"], host)
    only_js_links = sorted(set(ren["links"]) - set(raw["links"]))
    raw_words = set(raw["text"].lower().split()); ren_words = ren["text"].lower().split()
    js_words = [w for w in ren_words if w not in raw_words]
    res = {"url": url, "status": r["status"],
           "raw": {k: v for k, v in raw.items() if k not in ("text", "links")} | {"links": len(raw["links"])},
           "rendered": {k: v for k, v in ren.items() if k not in ("text", "links")} | {"links": len(ren["links"])},
           "links_only_after_js": only_js_links[:50],
           "pct_words_only_after_js": round(100 * len(js_words) / max(1, len(ren_words)), 1),
           "pct_links_only_after_js": round(100 * len(only_js_links) / max(1, len(ren["links"])), 1)}
    sev, why = "ok", []
    if (raw["robots"] or "") != (ren["robots"] or "") or raw["canonical"] != ren["canonical"]:
        sev = "critical"; why.append("robots/canonical changes after JS: raw %s %s vs rendered %s %s" % (raw["robots"], raw["canonical"], ren["robots"], ren["canonical"]))
    if not raw["h1"] and ren["h1"]:
        sev = "critical"; why.append("H1 only after JS")
    if raw["words"] < 100 and ren["words"] > 300:
        sev = "critical"; why.append("body text only after JS (raw %d words vs %d)" % (raw["words"], ren["words"]))
    if sev == "ok" and (res["pct_words_only_after_js"] > 30 or res["pct_links_only_after_js"] > 20):
        sev = "high"; why.append("%s%% words / %s%% links only after JS" % (res["pct_words_only_after_js"], res["pct_links_only_after_js"]))
    if sev == "ok" and (raw["title"] != ren["title"] or raw["desc"] != ren["desc"] or (raw["ld_blocks"] == 0 and ren["ld_blocks"] > 0)):
        sev = "medium"; why.append("title/desc/JSON-LD differ raw vs rendered")
    res["severity"], res["why"] = sev, why
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", T.urllib.parse.urlsplit(url).path.strip("/") or "home")[:80]
    json.dump(res, open(os.path.join(out, "render-%s.json" % slug), "w"), indent=1)
    return res

def main():
    a = sys.argv[1:]
    if not a or "-h" in a:
        print(__doc__); sys.exit(1)
    out = a[a.index("--out") + 1] if "--out" in a else "."
    urls = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] != "--out")]
    os.makedirs(out, exist_ok=True)
    L = ["| URL | sev | raw words | rendered words | raw links | rendered links | JS-only links | raw H1 | JSON-LD raw/rendered | why |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for u in urls:
        u = u if u.startswith("http") else "https://" + u
        try:
            r = check(u, out)
        except Exception as e:
            L.append("| %s | ERR | %s |||||||||" % (u, str(e)[:80])); continue
        L.append("| %s | %s | %d | %d | %d | %d | %d | %s | %d/%d | %s |" % (
            u, r["severity"], r["raw"]["words"], r["rendered"]["words"], r["raw"]["links"], r["rendered"]["links"],
            len(r["links_only_after_js"]), "yes" if r["raw"]["h1"] else "NO", r["raw"]["ld_blocks"], r["rendered"]["ld_blocks"],
            "; ".join(r["why"])[:160]))
        sys.stderr.write("rendered %s\n" % u)
    open(os.path.join(out, "render.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
