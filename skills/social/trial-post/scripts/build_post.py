#!/usr/bin/env python3
"""Build the exact Zernio `posts_create_post` arguments for ONE platform, after the safety checks.

usage: build_post.py --platform instagram|tiktok --idea R6 --hook A --video final.mp4 --media-url https://... --caption CAPTION.txt
                     [--now | --at 2026-11-02T18:05:00] [--ai] [--tag mytag] [--config config.json]

Refuses (exit 2, nothing written) when:
  - a STOP file exists ($HOME/.trial-post/STOP): a previous post failed a check; a human clears it
  - the same video file (sha256) is already posted on this platform (ledger)
  - the platform's last post is inside the spacing gap and --now was asked (prints the earliest allowed time)
  - today's cap for the platform is used up
  - the caption has an em dash; a TikTok caption says "comment" or lacks your bio line
Prints the arguments JSON and saves a plan in $HOME/.trial-post/plans/<plan>.json. Copy the printed JSON into
the MCP tool call EXACTLY: mcp__zernio__call_tool name="posts_create_post" arguments=<printed JSON>.
Never use posts_create (the simple tool): on Instagram it publishes a normal FEED reel, not a trial.
"""
import argparse, datetime as dt, json, os, re, sys, uuid
from zoneinfo import ZoneInfo
from tp_common import load_config, ledger_rows, sha256, now

HOME = os.path.join(os.path.expanduser("~"), ".trial-post")


def refuse(msg):
    print("REFUSED:", msg); sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", required=True, choices=["instagram", "tiktok"])
    ap.add_argument("--video", required=True); ap.add_argument("--media-url", required=True)
    ap.add_argument("--caption", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--now", action="store_true"); g.add_argument("--at", help="local wall-clock time in config timezone")
    ap.add_argument("--ai", action="store_true", help="AI avatar / AI-generated footage: sets the platform AI flag")
    ap.add_argument("--idea", required=True, help="idea / body id from the record sheet, e.g. R6")
    ap.add_argument("--hook", required=True, help="hook id, e.g. A; the scorecard compares hooks within an idea")
    ap.add_argument("--tag", action="append", default=[]); ap.add_argument("--config")
    a = ap.parse_args()
    cfg = load_config(a.config); p = a.platform; tz = ZoneInfo(cfg["timezone"])

    if os.path.exists(os.path.join(HOME, "STOP")):
        refuse(f"STOP file present ({os.path.join(HOME, 'STOP')}): read it, fix the cause, delete it by hand")
    if not a.media_url.startswith("https://"):
        refuse("media url must be the https public URL returned by the upload")
    cap = open(a.caption, encoding="utf-8").read().strip()
    if not cap:
        refuse("empty caption")
    if "\u2014" in cap:
        refuse("caption has an em dash")
    if p == "tiktok":
        if re.search(r"\bcomment\b", cap, re.I):
            refuse("TikTok caption says 'comment': keyword DMs do not work there, use the bio ending + bio line")
        bio = cfg.get("bio_line")
        if bio and bio.lower() not in cap.lower():
            refuse(f"TikTok caption lacks the bio line '{bio}'")

    sha = sha256(a.video)
    rows = [r for r in ledger_rows(cfg) if r.get("platform") == p and r.get("status") in ("published", "scheduled", "publishing")]
    if any(r.get("sha256") == sha for r in rows):
        refuse(f"this exact file is already on {p} (ledger). Make a genuinely different edit or skip it")
    t_now = now()
    when = t_now if a.now else dt.datetime.fromisoformat(a.at).replace(tzinfo=tz).astimezone(dt.timezone.utc)
    day = when.astimezone(tz).date()
    same_day = [r for r in rows if dt.datetime.fromisoformat(r["when"]).astimezone(tz).date() == day]
    if len(same_day) >= cfg["daily_cap"][p]:
        refuse(f"{p} daily cap {cfg['daily_cap'][p]} used on {day}")
    gap = dt.timedelta(minutes=cfg["spacing_minutes"][p])
    for r in rows:
        t = dt.datetime.fromisoformat(r["when"])
        if abs(when - t) < gap:
            earliest = (t + gap + dt.timedelta(seconds=60)).astimezone(tz).strftime("%Y-%m-%dT%H:%M:00")
            refuse(f"inside the {gap} gap of the {p} post at {t.astimezone(tz)}; earliest: --at {earliest}")

    plan = uuid.uuid4().hex[:10]
    target = {"platform": p, "accountId": cfg["accounts"][p]}
    args = {"content": cap, "media_items": [{"type": "video", "url": a.media_url}], "platforms": [target],
            "timezone": cfg["timezone"], "metadata": {"source": "trial-post", "plan": plan, "idea": a.idea, "hook": a.hook},
            "tags": ["trial-post", f"idea-{a.idea}", f"hook-{a.hook}"] + a.tag}
    if p == "instagram":
        target["platformSpecificData"] = {"trialParams": {"graduationStrategy": "MANUAL"}, "isAiGenerated": bool(a.ai)}
    else:
        tk = cfg.get("tiktok", {})
        args["tiktok_settings"] = {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True,
                                   "allow_duet": bool(tk.get("allow_duet")), "allow_stitch": bool(tk.get("allow_stitch")),
                                   "content_preview_confirmed": True, "express_consent_given": True,
                                   "video_made_with_ai": bool(a.ai)}
    if a.now:
        args["publish_now"] = True
    else:
        args["scheduled_for"] = a.at
    os.makedirs(os.path.join(HOME, "plans"), exist_ok=True)
    json.dump({"plan": plan, "platform": p, "idea": a.idea, "hook": a.hook, "video": os.path.abspath(a.video), "sha256": sha, "when": when.isoformat(),
               "args": args, "made": t_now.isoformat()}, open(os.path.join(HOME, "plans", plan + ".json"), "w"), indent=1)
    print(f"# plan {plan}: call mcp__zernio__call_tool name=posts_create_post with exactly these arguments")
    print(json.dumps(args, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
