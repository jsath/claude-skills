#!/usr/bin/env python3
"""72-hour scorecard: which hook won each idea, what to graduate, what to kill, which ideas to retire.

usage: scorecard.py --ledger $HOME/.trial-post/ledger.jsonl --analytics a1.txt [a2.txt ...]
                    [--config config.json] [--out SCORECARD.md]

--analytics: saved results of Zernio analytics_get_analytics (JSON or Python-repr text), or a CSV export with
columns post_id, platform, views, skip_rate, avg_watch_s, duration_s, completion_rate, published_at, last_updated.
Only rows whose metric age (last_updated - published_at) sits inside window_hours are scored: same source, same
window, or the numbers are not compared. Rows outside the window are listed as "not in window yet".

Instagram, per idea: hold = average watch / video length. Graduate candidate = lowest skip with hold >= min_hold,
skip < max_skip and views >= min_views. Best skip and best hold on different hooks = split, the creator picks.
A gap under tie_points = tie. Kill = skip >= kill_skip_pct. Retire the idea when every hook is >= the retire skip
AND under the retire views. TikTok: ranked by completion rate, For You share shown next to it when present.
Graduation itself is the creator's tap in the Instagram app ("Share to everyone"); this only recommends.
"""
import argparse, ast, csv, datetime as dt, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def parse_any(path):
    txt = open(path, encoding="utf-8").read().strip()
    if path.endswith(".csv"):
        return list(csv.DictReader(open(path, encoding="utf-8")))
    for loader in (json.loads, ast.literal_eval):
        try:
            return loader(txt)
        except Exception:
            pass
    raise SystemExit(f"cannot parse {path}")


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def f(v):
    try:
        return float(str(v).replace(",", "").rstrip("%"))
    except (TypeError, ValueError):
        return None


def ts(v):
    if not v:
        return None
    try:
        return dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def metrics(d):
    pid = d.get("post_id") or d.get("postId") or d.get("_id") or d.get("id")
    an = d.get("analytics") if isinstance(d.get("analytics"), dict) else d
    watch = f(an.get("igReelsAvgWatchTime"))
    watch = watch / 1000 if watch is not None else f(an.get("avg_watch_s"))
    return {"post_id": pid, "platform": (d.get("platform") or "").lower(), "views": f(an.get("views")),
            "skip": f(an.get("reelsSkipRate", an.get("skip_rate"))), "watch_s": watch,
            "dur_s": f(an.get("videoDurationSeconds", an.get("duration_s"))),
            "completion": f(an.get("completionRate", an.get("completion_rate"))),
            "foryou": f((an.get("impressionSources") or {}).get("forYou")) if isinstance(an.get("impressionSources"), dict) else None,
            "published": ts(d.get("publishedAt", d.get("published_at"))),
            "updated": ts(an.get("lastUpdated", d.get("lastUpdated", d.get("last_updated"))))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.expanduser("~/.trial-post/ledger.jsonl"))
    ap.add_argument("--analytics", nargs="+", required=True)
    ap.add_argument("--config", default=os.path.join(HERE, "..", "config.json")); ap.add_argument("--out")
    a = ap.parse_args()
    cfg = json.load(open(a.config if os.path.exists(a.config) else os.path.join(HERE, "..", "config.example.json")))
    led = {r["post_id"]: r for r in (json.loads(l) for l in open(a.ledger) if l.strip())}
    rows = {}
    for p in a.analytics:
        for d in walk(parse_any(p)):
            m = metrics(d)
            if m["post_id"] in led and (m["views"] is not None or m["completion"] is not None):
                rows[m["post_id"]] = m
    lo, hi = cfg["window_hours"]
    ig, out, pending = cfg["instagram"], [], []
    ideas = {}
    for pid, m in rows.items():
        r = led[pid]; m.update(idea=r.get("idea") or "?", hook=r.get("hook") or "?", platform=r["platform"])
        age = (m["updated"] - m["published"]).total_seconds() / 3600 if m["updated"] and m["published"] else None
        m["age"] = age
        if age is None or not (lo <= age <= hi):
            pending.append(m); continue
        m["hold"] = round(100 * m["watch_s"] / m["dur_s"], 1) if m["watch_s"] and m["dur_s"] else None
        ideas.setdefault((m["idea"], m["platform"]), []).append(m)

    out.append(f"# Scorecard ({dt.date.today()}, window {lo} to {hi} h)\n")
    for (idea, plat), ms in sorted(ideas.items()):
        out.append(f"## {idea} on {plat}")
        if plat == "instagram":
            out.append("| hook | views | skip % | hold % | verdict |\n|---|---|---|---|---|")
            g = ig["graduate"]
            ok = [m for m in ms if m["skip"] is not None and m["hold"] is not None and m["skip"] < g["max_skip_pct"]
                  and m["hold"] >= g["min_hold_pct"] and (m["views"] or 0) >= g["min_views"]]
            best_skip = min((m for m in ms if m["skip"] is not None), key=lambda m: m["skip"], default=None)
            best_hold = max((m for m in ms if m["hold"] is not None), key=lambda m: m["hold"], default=None)
            cand = min(ok, key=lambda m: m["skip"], default=None)
            for m in sorted(ms, key=lambda m: (m["skip"] is None, m["skip"] or 0)):
                v = "KILL" if m["skip"] is not None and m["skip"] >= ig["kill_skip_pct"] else ""
                if cand is m:
                    v = "GRADUATE candidate"
                out.append(f"| {m['hook']} | {int(m['views'] or 0):,} | {m['skip']} | {m['hold']} | {v} |")
            if best_skip and best_hold and best_skip is not best_hold:
                out.append(f"Split: best skip = hook {best_skip['hook']}, best hold = hook {best_hold['hook']}. You pick.")
            if cand:
                close = [m for m in ok if m is not cand and abs(m["skip"] - cand["skip"]) < ig["tie_points"]]
                if close:
                    out.append(f"Tie (within {ig['tie_points']} points): hooks {cand['hook']}, " + ", ".join(m["hook"] for m in close))
            rt = ig["retire"]
            if ms and all(m["skip"] is not None and m["skip"] >= rt["all_skip_pct_at_least"] and (m["views"] or 0) < rt["views_under"] for m in ms):
                out.append("RETIRE this idea on Instagram: every hook lost.")
        else:
            out.append("| hook | views | completion % | For You % |\n|---|---|---|---|")
            for m in sorted(ms, key=lambda m: -(m["completion"] or 0)):
                out.append(f"| {m['hook']} | {int(m['views'] or 0):,} | {m['completion']} | {m['foryou'] if m['foryou'] is not None else ''} |")
        out.append("")
    if pending:
        out.append("## Not in window yet (no decisions)")
        for m in pending:
            out.append(f"- {m.get('idea')} hook {m.get('hook')} on {m['platform']}: age {round(m['age'], 1) if m['age'] else 'unknown'} h")
    out.append("\nViews are shown, never used alone. Follows are not in the API for reels: check them in the app before graduating.")
    txt = "\n".join(out) + "\n"
    if a.out:
        open(a.out, "w").write(txt)
    print(txt)


if __name__ == "__main__":
    sys.exit(main())
