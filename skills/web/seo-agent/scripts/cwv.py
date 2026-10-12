#!/usr/bin/env python3
"""Core Web Vitals module for the seo-agent skill (lab + field).

Lab:   local Lighthouse CLI (npm i -g lighthouse) on mobile AND desktop for each
       URL. Captures perf score, LCP, CLS, TBT (the lab proxy for INP), FCP,
       Speed Index, total byte weight, LCP element, render-blocking resources,
       unused JS, image savings and third-party script weight by entity.
Field: CrUX real-user p75 (LCP, CLS, INP, FCP, TTFB) per URL and per origin,
       via the CrUX API (needs a Google API key with the CrUX API enabled) and
       falling back to the PageSpeed Insights API loadingExperience block
       (no key needed at low volume). Key lookup: $PSI_KEY, $CRUX_KEY, or
       ~/.config/seo-agent/psi-key.

Lab numbers are one run from THIS machine's network; label them "lab, local".
Field numbers are what Google ranks on. Never mix the two in one claim.

Usage:
  python3 cwv.py --out DIR [--runs 1] [--no-lab] [--no-field] <url> [<url> ...]
Writes DIR/lighthouse/<slug>-<form>.json, DIR/cwv-summary.json, DIR/cwv.md
Exit code 0 even when some runs fail (failures are listed in the summary).
"""
import sys, os, json, re, subprocess, urllib.request, urllib.parse, shutil, statistics

CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]

def api_key():
    for k in ("PSI_KEY", "CRUX_KEY"):
        if os.environ.get(k):
            return os.environ[k].strip()
    p = os.path.expanduser("~/.config/seo-agent/psi-key")
    if os.path.isfile(p):
        return open(p).read().strip()
    return None

def slug(url):
    s = re.sub(r"^https?://[^/]+", "", url).strip("/") or "home"
    return re.sub(r"[^a-zA-Z0-9]+", "-", s)[:80]

# ---------------------------------------------------------------- lab
def lighthouse(url, form, outdir):
    lh = shutil.which("lighthouse")
    if not lh:
        return {"error": "lighthouse CLI not installed (npm i -g lighthouse)"}
    chrome = next((c for c in CHROME_CANDIDATES if c and os.path.exists(c)), None)
    env = dict(os.environ)
    if chrome:
        env["CHROME_PATH"] = chrome
    path = os.path.join(outdir, "lighthouse", "%s-%s.json" % (slug(url), form))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [lh, url, "--only-categories=performance", "--output=json",
           "--output-path=" + path, "--quiet",
           "--chrome-flags=--headless=new --no-sandbox"]
    if form == "desktop":
        cmd.append("--preset=desktop")
    try:
        subprocess.run(cmd, env=env, timeout=240, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except Exception as e:
        return {"error": "lighthouse failed: %s" % str(e)[:200]}
    return parse_lh(json.load(open(path)))

def parse_lh(d):
    a = d.get("audits", {})
    nv = lambda k: a.get(k, {}).get("numericValue")
    out = {
        "score": round((d.get("categories", {}).get("performance", {}).get("score") or 0) * 100),
        "lcp_ms": nv("largest-contentful-paint"),
        "cls": nv("cumulative-layout-shift"),
        "tbt_ms": nv("total-blocking-time"),
        "fcp_ms": nv("first-contentful-paint"),
        "si_ms": nv("speed-index"),
        "ttfb_ms": nv("server-response-time"),
        "bytes": nv("total-byte-weight"),
        "lighthouse": d.get("lighthouseVersion"),
    }
    # LCP element
    try:
        items = a["largest-contentful-paint-element"]["details"]["items"]
        node = items[0]["items"][0]["node"] if "items" in items[0] else items[0]["node"]
        out["lcp_element"] = (node.get("selector", "") + " | " + node.get("snippet", ""))[:200]
    except Exception:
        pass
    # opportunities with savings
    opps = []
    for k in ("render-blocking-resources", "unused-javascript", "unused-css-rules",
              "modern-image-formats", "uses-responsive-images", "offscreen-images",
              "efficient-animated-content", "uses-optimized-images", "legacy-javascript",
              "font-display", "unminified-javascript", "uses-text-compression"):
        au = a.get(k, {})
        det = au.get("details", {}) or {}
        ms = det.get("overallSavingsMs") or 0
        by = det.get("overallSavingsBytes") or 0
        if (au.get("score") is not None and au.get("score") < 0.9) and (ms > 50 or by > 20000):
            opps.append({"audit": k, "savings_ms": round(ms), "savings_kb": round(by / 1024)})
    out["opportunities"] = opps
    # third parties
    tp = []
    try:
        for it in a["third-party-summary"]["details"]["items"]:
            ent = it.get("entity")
            name = ent.get("text") if isinstance(ent, dict) else ent
            tp.append({"entity": name, "kb": round((it.get("transferSize") or 0) / 1024),
                       "blocking_ms": round(it.get("blockingTime") or 0),
                       "main_thread_ms": round(it.get("mainThreadTime") or 0)})
    except Exception:
        pass
    out["third_parties"] = sorted(tp, key=lambda x: -x["kb"])[:12]
    # bootup / mainthread
    out["mainthread_ms"] = nv("mainthread-work-breakdown")
    out["js_bootup_ms"] = nv("bootup-time")
    return out

def median_runs(runs):
    ok = [r for r in runs if "error" not in r]
    if not ok:
        return runs[0] if runs else {"error": "no runs"}
    if len(ok) == 1:
        return ok[0]
    # take the run with median score, report medians for core metrics
    ok.sort(key=lambda r: r["score"])
    base = dict(ok[len(ok) // 2])
    for k in ("lcp_ms", "cls", "tbt_ms", "fcp_ms", "si_ms"):
        vals = [r[k] for r in ok if r.get(k) is not None]
        if vals:
            base[k] = statistics.median(vals)
    base["runs"] = len(ok)
    return base

# ---------------------------------------------------------------- field
def crux(url=None, origin=None, form=None, key=None):
    if not key:
        return {"error": "no API key"}
    body = {"url": url} if url else {"origin": origin}
    if form:
        body["formFactor"] = form
    req = urllib.request.Request(
        "https://chromeuxreport.googleapis.com/v1/records:queryRecord?key=" + key,
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:200]
        return {"error": "CrUX %d: %s" % (e.code, "no field data (below traffic threshold)" if e.code == 404 else msg)}
    except Exception as e:
        return {"error": "CrUX: %s" % e}
    m = d.get("record", {}).get("metrics", {})
    def p(k):
        v = m.get(k, {}).get("percentiles", {}).get("p75")
        try: return float(v) if v is not None else None
        except ValueError: return None
    return {"lcp_ms": p("largest_contentful_paint"), "cls": p("cumulative_layout_shift"),
            "inp_ms": p("interaction_to_next_paint"), "fcp_ms": p("first_contentful_paint"),
            "ttfb_ms": p("experimental_time_to_first_byte"),
            "period": d.get("record", {}).get("collectionPeriod")}

def psi_field(url, form, key=None):
    params = {"url": url, "strategy": form, "category": "PERFORMANCE"}
    if key:
        params["key"] = key
    try:
        d = json.loads(urllib.request.urlopen(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(params),
            timeout=90).read())
    except urllib.error.HTTPError as e:
        return {"error": "PSI %d: %s" % (e.code, e.read().decode()[:160])}
    except Exception as e:
        return {"error": "PSI: %s" % e}
    def block(le):
        m = le.get("metrics", {})
        p = lambda k: (m.get(k) or {}).get("percentile")
        return {"lcp_ms": p("LARGEST_CONTENTFUL_PAINT_MS"), "cls": (p("CUMULATIVE_LAYOUT_SHIFT_SCORE") or 0) / 100 if p("CUMULATIVE_LAYOUT_SHIFT_SCORE") is not None else None,
                "inp_ms": p("INTERACTION_TO_NEXT_PAINT"), "fcp_ms": p("FIRST_CONTENTFUL_PAINT_MS"),
                "ttfb_ms": p("EXPERIMENTAL_TIME_TO_FIRST_BYTE"),
                "overall": le.get("overall_category"), "origin_fallback": le.get("origin_fallback", False)}
    le, ole = d.get("loadingExperience") or {}, d.get("originLoadingExperience") or {}
    lab = d.get("lighthouseResult")
    return {"url_field": block(le) if le.get("metrics") else None,
            "origin_field": block(ole) if ole.get("metrics") else None,
            "psi_lab": parse_lh(lab) if lab else None}

# ---------------------------------------------------------------- grading
def grade(metric, v):
    if v is None:
        return "n/a"
    t = {"lcp_ms": (2500, 4000), "cls": (0.1, 0.25), "inp_ms": (200, 500),
         "tbt_ms": (200, 600), "fcp_ms": (1800, 3000), "ttfb_ms": (800, 1800)}[metric]
    return "good" if v <= t[0] else ("needs-improvement" if v <= t[1] else "poor")

def fmt_ms(v):
    return "-" if v is None else ("%.1fs" % (v / 1000) if v >= 1000 else "%dms" % v)

def main():
    args = sys.argv[1:]
    if not args or "-h" in args:
        print(__doc__); sys.exit(1)
    out = "."
    runs = 1
    lab = "--no-lab" not in args
    field = "--no-field" not in args
    urls = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--out": out = args[i + 1]; i += 2; continue
        if a == "--runs": runs = int(args[i + 1]); i += 2; continue
        if a.startswith("--"): i += 1; continue
        urls.append(a if a.startswith("http") else "https://" + a); i += 1
    os.makedirs(out, exist_ok=True)
    key = api_key()
    summ_path = os.path.join(out, "cwv-summary.json")
    summary = json.load(open(summ_path)) if os.path.isfile(summ_path) else {"pages": {}, "origin": {}}
    if field and urls:
        origin = re.match(r"https?://[^/]+", urls[0]).group(0)
        for form in ("PHONE", "DESKTOP"):
            summary["origin"][form] = crux(origin=origin, form=form, key=key)
    for u in urls:
        rec = summary["pages"].setdefault(u, {})
        for form in ("mobile", "desktop"):
            if lab:
                rs = [lighthouse(u, form, out) for _ in range(runs)]
                rec["lab_" + form] = median_runs(rs)
            if field:
                c = crux(url=u, form="PHONE" if form == "mobile" else "DESKTOP", key=key)
                rec["crux_" + form] = c
                if "error" in c and "below traffic threshold" not in c["error"]:
                    # CrUX API blocked/not enabled: PSI carries the same CrUX data
                    # (URL-level, else origin fallback) plus a Google-hosted lab run.
                    rec["psi_" + form] = psi_field(u, form, key)
            sys.stderr.write("done %s %s\n" % (form, u))
            json.dump(summary, open(summ_path, "w"), indent=1)   # persist as we go
    json.dump(summary, open(summ_path, "w"), indent=1)
    # markdown
    L = ["| URL | form | score | LCP | CLS | TBT | FCP | weight | top 3rd party |", "|---|---|---|---|---|---|---|---|---|"]
    for u, rec in summary["pages"].items():
        for form in ("mobile", "desktop"):
            r = rec.get("lab_" + form)
            if not r: continue
            if "error" in r:
                L.append("| %s | %s | ERR | %s |||||" % (u, form, r["error"][:60])); continue
            tp = (r.get("third_parties") or [{}])[0]
            L.append("| %s | %s | %d | %s (%s) | %.3f (%s) | %s (%s) | %s | %dKB | %s %sKB |" % (
                re.sub(r"^https?://[^/]+", "", u) or "/", form, r["score"],
                fmt_ms(r["lcp_ms"]), grade("lcp_ms", r["lcp_ms"]), r["cls"] or 0, grade("cls", r["cls"]),
                fmt_ms(r["tbt_ms"]), grade("tbt_ms", r["tbt_ms"]), fmt_ms(r["fcp_ms"]),
                (r.get("bytes") or 0) / 1024, tp.get("entity", "-"), tp.get("kb", "")))
    L.append("\nPSI (Google-hosted) lab + field, per URL:")
    L.append("| URL | form | PSI score | PSI LCP | PSI TBT | field LCP | field CLS | field INP | field source |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for u, rec in summary["pages"].items():
        for form in ("mobile", "desktop"):
            ps = rec.get("psi_" + form)
            if not ps: continue
            if "error" in ps:
                L.append("| %s | %s | ERR %s |||||||" % (u, form, ps["error"][:60])); continue
            lb = ps.get("psi_lab") or {}
            f = ps.get("url_field") or {}
            src = "none" if not f else ("origin (URL below threshold)" if f.get("origin_fallback") else "URL")
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                re.sub(r"^https?://[^/]+", "", u) or "/", form, lb.get("score", "-"), fmt_ms(lb.get("lcp_ms")),
                fmt_ms(lb.get("tbt_ms")), fmt_ms(f.get("lcp_ms")), f.get("cls"), fmt_ms(f.get("inp_ms")), src))
    L.append("\nField (CrUX API p75):")
    for form, o in summary.get("origin", {}).items():
        L.append("- origin %s: %s" % (form, o.get("error") or "LCP %s, CLS %s, INP %s" % (
            fmt_ms(o.get("lcp_ms")), o.get("cls"), fmt_ms(o.get("inp_ms")))))
    open(os.path.join(out, "cwv.md"), "w").write("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
