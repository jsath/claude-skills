#!/usr/bin/env python3
"""PageSpeed Insights for the seo-agent skill.

Unlocks Core Web Vitals (LCP/CLS/INP) + lab TBT, the audit dimension the
crawler can't reach. Free, no key needed for low volume (set PSI_KEY env to
raise quota). Mobile strategy by default (Google indexes mobile-first).

Usage:
  python3 psi.py <url> [<url> ...]
  python3 psi.py https://www.example.com/ https://www.example.com/blog/some-post
"""
import sys, os, json, urllib.request, urllib.parse

def run(url, strategy="mobile"):
    key = os.environ.get("PSI_KEY")
    params = {"url": url, "strategy": strategy, "category": "PERFORMANCE"}
    if key:
        params["key"] = key
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(api, headers={"User-Agent": "seo-agent-psi"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def fmt(url, d):
    le = d.get("loadingExperience", {})
    lab = d.get("lighthouseResult", {}).get("audits", {})
    def metric(node, key, label):
        if not node: return None
        m = node.get(key) if key in node else None
        if isinstance(m, dict) and "percentile" in m:
            return (label, m["percentile"], m.get("category", "?"))
        return None
    # field CWV (real-user)
    f_lcp = metric(le, "LARGEST_CONTENTFUL_PAINT_MS", "LCP")
    f_cls = metric(le, "CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS")
    f_inp = metric(le, "INTERACTION_TO_NEXT_PAINT", "INP")
    # lab
    l_lcp = lab.get("largest-contentful-paint", {}).get("numericValue")
    l_cls = lab.get("cumulative-layout-shift", {}).get("numericValue")
    l_tbt = lab.get("total-blocking-time", {}).get("numericValue")
    perf  = d.get("lighthouseResult", {}).get("categories", {}).get("performance", {}).get("score")
    print("\n### %s" % url)
    if perf is not None:
        print("  PERF SCORE : %d/100" % round(perf * 100))
    def show(label, val, unit="", scale=""):
        if val is None: return
        if isinstance(val, float) and val < 100 and unit == "ms": val = "%.0f" % val
        print(("  %-10s : %s %s %s" % (label, val, unit, ("(%s)" % scale) if scale else "")).rstrip())
    # field data first (what Google actually uses for ranking)
    if f_lcp: show("CWV LCP", f_lcp[1] / 1000.0, "s", f_lcp[2])
    if f_cls: show("CWV CLS", "%.3f" % f_cls[1], "", f_cls[2])
    if f_inp: show("CWV INP", f_inp[1], "ms", f_inp[2])
    if l_lcp: show("lab LCP", l_lcp / 1000.0, "s")
    if l_cls: show("lab CLS", "%.3f" % l_cls)
    if l_tbt: show("lab TBT", l_tbt, "ms")
    if not any([f_lcp, f_cls, f_inp, l_lcp, l_cls, l_tbt]):
        print("  (no perf data, URL may be unreachable or PSI quota hit)")

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    for url in sys.argv[1:]:
        url = url if url.startswith("http") else "https://" + url
        try:
            fmt(url, run(url))
        except Exception as e:
            print("\n### %s\n  ERR %s" % (url, str(e)[:200]))

if __name__ == "__main__":
    main()
