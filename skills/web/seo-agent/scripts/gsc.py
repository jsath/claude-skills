#!/usr/bin/env python3
"""Google Search Console access for the seo-agent skill.

The one data source that turns blind SERP inference into measured prioritization
AND closes the outcome loop (did the fix move impressions/position?).

Auth (first match wins):
  1. Service account JSON via $GSC_SERVICE_ACCOUNT_JSON or --creds (add the
     service-account email as a RESTRICTED user on the GSC property).
  2. Application Default Credentials (user OAuth): run
       gcloud auth application-default login \
         --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform
     Uses your own Google login; works when the org blocks SA key creation.
Deps: google-auth  (pip install google-auth).

Usage:
  python3 gsc.py <property> searchanalytics [--days 28] [--dim page|query] [--top 50]
                                            [--start YYYY-MM-DD --end YYYY-MM-DD]
                                            [--url <page-url>]   # filter to one page
  python3 gsc.py <property> inspect <url>
  python3 gsc.py <property> preflight       # auth + property access + sitemap status; run first
  python3 gsc.py <property> snapshot        # save state + diff vs previous snapshot

  <property> is the sc-domain: e.g. sc-domain:example.com  (or https://www.example.com/)

snapshot writes ~/.claude/seo-state/<host>/gsc-<date>.json (28d window, top pages
+ queries) and prints position/impression movers vs the previous snapshot, the
"did the fixes work?" signal, and the before/after series for reporting.
"""
import sys, os, json, urllib.request, urllib.parse, datetime

SC_BASE = "https://searchconsole.googleapis.com/webmasters/v3"
SC_V1 = "https://searchconsole.googleapis.com/v1"

def die(msg, code=1):
    sys.stderr.write(msg + "\n"); sys.exit(code)

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

def creds():
    try:
        from google.auth.transport.requests import Request
    except ImportError:
        die("Missing dependency. Install with:  pip install google-auth")

    path = None
    if "--creds" in sys.argv:
        path = sys.argv[sys.argv.index("--creds") + 1]
    path = path or os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if path and not os.path.isfile(path):
        # Known trap: the env var points at a key file that was never
        # created, so the SA path is skipped silently and the dead ADC path fails.
        sys.stderr.write("WARN: service-account key %s does not exist; falling back to ADC.\n" % path)

    if path and os.path.isfile(path) and os.path.getsize(path) > 0:
        from google.oauth2 import service_account
        sa = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        sa.refresh(Request())
        return sa.token

    # Fall back to Application Default Credentials (user OAuth via gcloud).
    try:
        import google.auth
        adc, project = google.auth.default(scopes=SCOPES)
        adc.refresh(Request())
        global QUOTA_PROJECT
        # Only send x-goog-user-project when ADC carries an EXPLICIT quota
        # project. Falling back to the gcloud default project sent a project the
        # user lacked serviceusage.services.use on, which 403s. Search Console
        # bills the property owner, so no header is the safer default.
        QUOTA_PROJECT = getattr(adc, "quota_project_id", None)
        return adc.token
    except Exception as e:
        die("No usable credentials. Either set $GSC_SERVICE_ACCOUNT_JSON to a "
            "service-account JSON, or run:\n"
            "  gcloud auth application-default login "
            "--scopes=https://www.googleapis.com/auth/webmasters.readonly,"
            "https://www.googleapis.com/auth/cloud-platform\n"
            "(ADC error: %s)" % e)

QUOTA_PROJECT = None

def api(method, path, token, body=None, base=None):
    url = (base or SC_BASE) + path
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    if QUOTA_PROJECT:
        req.add_header("x-goog-user-project", QUOTA_PROJECT)
    if body is not None:
        req.data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        die("GSC API %s error %d: %s" % (method, e.code, e.read().decode()[:400]))

def sa_query(prop, token, start, end, dim, top, url_filter=None):
    body = {"startDate": start, "endDate": end,
            "dimensions": [dim], "rowLimit": int(top)}
    if url_filter:
        body["dimensionFilterGroups"] = [{"filters": [
            {"dimension": "page", "operator": "equals", "expression": url_filter}]}]
    res = api("POST", "/sites/%s/searchAnalytics/query" % urllib.parse.quote(prop, safe=""),
              token, body)
    return res.get("rows", [])

def searchanalytics(prop, token, days=28, dim="page", top=50,
                    start=None, end=None, url_filter=None):
    if not end:
        end = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()  # GSC lags ~2d
    if not start:
        start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=days)).isoformat()
    rows = sa_query(prop, token, start, end, dim, top, url_filter)
    if not rows:
        print("No GSC data for %s in %s..%s (property may be unverified or new)." % (prop, start, end))
        return
    print("GSC search analytics, %s, %s..%s by %s%s\n" % (
        prop, start, end, dim, (" for %s" % url_filter) if url_filter else ""))
    print("%-70s %8s %8s %8s %7s" % ("key", "clicks", "impr", "ctr", "pos"))
    for r in rows[:top]:
        k = r["keys"][0]
        print("%-70.70s %8d %8d %7.2f%% %7.1f" % (
            k, r["clicks"], r["impressions"], r["ctr"] * 100, r["position"]))

def inspect(prop, token, url):
    body = {"inspectionUrl": url, "siteUrl": prop}
    res = api("POST", "/urlInspection/index:inspect", token, body, base=SC_V1)
    ri = res.get("inspectionResult", {})
    idx = ri.get("indexStatusResult", {})
    print("URL inspection, %s\n" % url)
    print("  verdict        : %s" % idx.get("verdict", "?"))
    print("  coverageState  : %s" % idx.get("coverageState", "?"))
    print("  indexingState  : %s" % idx.get("indexingState", "?"))
    print("  lastCrawlTime  : %s" % idx.get("lastCrawlTime", "?"))
    print("  googleVerdict  : %s" % idx.get("googleVerdict", "?"))
    if idx.get("robotsTxtState"):
        print("  robotsTxtState : %s" % idx["robotsTxtState"])
    link = (ri.get("indexStatusResult", {}).get("sitemaps") or [])
    if link:
        print("  discovered via : %s" % ", ".join(link[:3]))

def snapshot(prop, token):
    end = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=28)).isoformat()
    pages = sa_query(prop, token, start, end, "page", 200)
    queries = sa_query(prop, token, start, end, "query", 500)
    host = prop.replace("sc-domain:", "").replace("https://", "").strip("/").replace("/", "_")
    d = os.path.join(os.path.expanduser("~/.claude/seo-state"), host)
    os.makedirs(d, exist_ok=True)
    today = datetime.date.today().isoformat()
    snap = {"taken": today, "window": [start, end],
            "pages": {r["keys"][0]: {"clicks": r["clicks"], "impressions": r["impressions"],
                                     "position": round(r["position"], 2)} for r in pages},
            "queries": {r["keys"][0]: {"clicks": r["clicks"], "impressions": r["impressions"],
                                       "position": round(r["position"], 2)} for r in queries}}
    path = os.path.join(d, "gsc-%s.json" % today)
    with open(path, "w") as f:
        json.dump(snap, f, indent=1)
    prior = sorted(p for p in os.listdir(d) if p.startswith("gsc-") and p < os.path.basename(path))
    print("Snapshot saved: %s (%d pages, %d queries)" % (path, len(pages), len(queries)))
    if not prior:
        print("No prior snapshot to diff (baseline established).")
        return
    prev = json.load(open(os.path.join(d, prior[-1])))
    print("Diff vs %s:" % prev["taken"])
    movers = []
    for u, cur in snap["pages"].items():
        old = prev["pages"].get(u)
        if not old:
            if cur["impressions"] >= 50: movers.append((u, "NEW", cur["impressions"], cur["position"], 0))
            continue
        dp = old["position"] - cur["position"]           # positive = improved
        di = cur["impressions"] - old["impressions"]
        if abs(dp) >= 1.0 or abs(di) >= 100:
            movers.append((u, "%+.1f pos" % dp, cur["impressions"], cur["position"], di))
    gone = [u for u in prev["pages"] if u not in snap["pages"] and prev["pages"][u]["impressions"] >= 100]
    if not movers and not gone:
        print("  no material page movement.")
    for u, tag, imp, pos, di in sorted(movers, key=lambda m: -abs(m[4]))[:20]:
        print("  %-70.70s %10s  now pos %5.1f  %6d impr (%+d)" % (u, tag, pos, imp, di))
    for u in gone[:5]:
        print("  DROPPED from top pages: %s" % u)

def preflight(prop, token):
    """Auth + access + sitemap status in one call. Run first; if it fails, stop
    spending time on GSC and label the run 'GSC unavailable'."""
    sites = api("GET", "/sites", token).get("siteEntry", [])
    mine = [x for x in sites if x.get("siteUrl") == prop]
    print("GSC preflight: token OK, %d properties visible" % len(sites))
    if not mine:
        die("Property %s NOT visible to this identity (wrong Google account?). Visible: %s"
            % (prop, ", ".join(x.get("siteUrl", "") for x in sites[:8])))
    print("  %s permission: %s" % (prop, mine[0].get("permissionLevel")))
    sm = api("GET", "/sites/%s/sitemaps" % urllib.parse.quote(prop, safe=""), token).get("sitemap", [])
    for m in sm:
        cont = m.get("contents", [{}])
        sub = sum(int(c.get("submitted", 0) or 0) for c in cont)
        idx = sum(int(c.get("indexed", 0) or 0) for c in cont)
        print("  sitemap %s  submitted=%d indexed=%s errors=%s warnings=%s lastDownloaded=%s pending=%s" % (
            m.get("path"), sub, idx or "n/a (API no longer reports)", m.get("errors"), m.get("warnings"),
            m.get("lastDownloaded"), m.get("isPending")))
    if not sm:
        print("  no sitemaps submitted for this property")
    print("  NOTE: Page Indexing, Crawl Stats, CWV and Manual Actions reports are UI-only (no API).")

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--") or "=" not in a]
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    prop, cmd = args[0], args[1]
    token = creds()
    if cmd == "searchanalytics":
        days = int(os.environ.get("GSC_DAYS", "28"))
        dim = "query"
        top = 50
        start = end = url_filter = None
        if "--days" in sys.argv: days = int(sys.argv[sys.argv.index("--days") + 1])
        if "--dim" in sys.argv: dim = sys.argv[sys.argv.index("--dim") + 1]
        if "--top" in sys.argv: top = int(sys.argv[sys.argv.index("--top") + 1])
        if "--start" in sys.argv: start = sys.argv[sys.argv.index("--start") + 1]
        if "--end" in sys.argv: end = sys.argv[sys.argv.index("--end") + 1]
        if "--url" in sys.argv: url_filter = sys.argv[sys.argv.index("--url") + 1]
        searchanalytics(prop, token, days, dim, top, start, end, url_filter)
    elif cmd == "snapshot":
        snapshot(prop, token)
    elif cmd == "preflight":
        preflight(prop, token)
    elif cmd == "inspect":
        if len(args) < 3: die("inspect needs a <url>")
        inspect(prop, token, args[2])
    else:
        die("Unknown command: %s (use preflight|searchanalytics|snapshot|inspect)" % cmd)

if __name__ == "__main__":
    main()
