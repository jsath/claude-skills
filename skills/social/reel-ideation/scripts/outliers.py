#!/usr/bin/env python3
"""Proof table for proven virals: each post vs its own creator's median, newest data only.

usage:
  outliers.py posts.jsonl [more.jsonl ...] [--days 14] [--min-likes 10000] [--min-multiple 3]
              [--metric likes|views] [--out PROOF.md]

Input: one JSON object per line (yt-dlp `-j` output works as is), or a CSV with a header row.
Fields read (any of these names):
  url        webpage_url | url | link
  creator    uploader_id | uploader | channel | creator | handle
  likes      like_count | likes
  views      view_count | views | play_count
  comments   comment_count | comments
  date       upload_date (YYYYMMDD) | timestamp (unix) | date (YYYY-MM-DD)
  title      title | description (first line)
  duration   duration (seconds)
  pinned     pinned (true = left out of the median: pinned posts are not a creator's normal)

The median for a creator is computed from ALL of that creator's posts in the input (not only the recent ones),
excluding pinned posts and the post being scored, so feed each creator's last 15 to 30 posts.
A post qualifies when it is inside --days AND (likes >= --min-likes OR multiple >= --min-multiple).
Missing numbers stay "unknown"; nothing is estimated. Exit 0 always; the table says what qualified.
"""
import argparse, csv, datetime as dt, json, statistics, sys

F = {
    "url": ["webpage_url", "url", "link"],
    "creator": ["uploader_id", "uploader", "channel", "creator", "handle"],
    "likes": ["like_count", "likes"],
    "views": ["view_count", "views", "play_count"],
    "comments": ["comment_count", "comments"],
    "title": ["title", "description"],
    "duration": ["duration"],
    "pinned": ["pinned"],
}


def pick(row, key):
    for k in F[key]:
        v = row.get(k)
        if v not in (None, ""):
            return v
    return None


def num(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def date_of(row):
    if row.get("upload_date"):
        try:
            return dt.datetime.strptime(str(row["upload_date"]), "%Y%m%d").date()
        except ValueError:
            pass
    if row.get("timestamp"):
        try:
            return dt.datetime.fromtimestamp(int(float(row["timestamp"])), dt.timezone.utc).date()
        except (ValueError, OSError):
            pass
    if row.get("date"):
        try:
            return dt.date.fromisoformat(str(row["date"])[:10])
        except ValueError:
            pass
    return None


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        head = f.read(1); f.seek(0)
        if head in "{[":
            txt = f.read().strip()
            if txt.startswith("["):
                rows = json.loads(txt)
            else:
                rows = [json.loads(ln) for ln in txt.splitlines() if ln.strip()]
        else:
            rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        t = pick(r, "title") or ""
        out.append({
            "url": pick(r, "url"), "creator": str(pick(r, "creator") or "unknown"),
            "likes": num(pick(r, "likes")), "views": num(pick(r, "views")), "comments": num(pick(r, "comments")),
            "date": date_of(r), "title": str(t).splitlines()[0][:80] if t else "",
            "duration": num(pick(r, "duration")),
            "pinned": str(pick(r, "pinned") or "").lower() in ("1", "true", "yes"),
        })
    return out


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--min-likes", type=int, default=10000)
    ap.add_argument("--min-multiple", type=float, default=3.0)
    ap.add_argument("--metric", choices=["likes", "views"], default="likes")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--out")
    a = ap.parse_args()
    posts = [p for f in a.files for p in load(f)]
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    since = today - dt.timedelta(days=a.days)
    by = {}
    for p in posts:
        by.setdefault(p["creator"], []).append(p)

    rows = []
    for c, ps in by.items():
        for p in ps:
            others = [q[a.metric] for q in ps if q is not p and not q["pinned"] and q[a.metric] is not None]
            med = statistics.median(others) if len(others) >= 3 else None
            val = p[a.metric]
            mult = round(val / med, 1) if (val is not None and med) else None
            recent = p["date"] is not None and p["date"] >= since
            ok = recent and ((p["likes"] or 0) >= a.min_likes or (mult or 0) >= a.min_multiple)
            rows.append((ok, val or 0, p, med, mult, len(others)))
    rows.sort(key=lambda r: (not r[0], -r[1]))

    lines = [f"# Proof table ({today.isoformat()}, window {a.days} d, floor {a.min_likes:,} likes or {a.min_multiple}x creator median {a.metric})", "",
             "| # | Creator | Link | Date | Likes | Comments | Views | Creator median (n) | Multiple | Length | Title |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    n = 0
    for ok, _, p, med, mult, k in rows:
        if not ok:
            continue
        n += 1
        medtxt = f"{int(med):,} ({k})" if med else f"unknown ({k} posts, need 3+)"
        lines.append(f"| {n} | {p['creator']} | {p['url'] or 'no link'} | {p['date'] or 'unknown'} | **{fmt(p['likes'])}** | {fmt(p['comments'])} | {fmt(p['views'])} | {medtxt} | {str(mult) + 'x' if mult else 'unknown'} | {str(p['duration']) + ' s' if p['duration'] else ''} | {p['title']} |")
    lines += ["", f"{n} of {len(posts)} posts qualified across {len(by)} creators.",
              "Numbers are as read from the input files at pull time; re-pull before quoting any of them on camera."]
    txt = "\n".join(lines) + "\n"
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
