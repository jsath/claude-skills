#!/usr/bin/env python3
"""Judge a Zernio create or get response for a plan, record it, and halt on anything unexpected.

usage: verify_post.py --plan <plan> --response response.txt [--config config.json]
Save the MCP tool result text (create response, or posts_get after publishing) to a file first.

Exit 0  ok: recorded in the ledger (Instagram: trial confirmed, isTrialReel true / MANUAL graduation)
Exit 4  still publishing: poll posts_get again in about a minute and re-run with the new response
Exit 3  STOP: Instagram response without trial proof, a failed or errored post, or no post id.
        Writes $HOME/.trial-post/STOP; build_post.py refuses until a human has looked and deletes it.
        Never "fix" it with an edit, delete or retry call: check the post in the app first.
"""
import argparse, json, os, sys
from tp_common import load_config, ledger_add, parse_response, now

HOME = os.path.join(os.path.expanduser("~"), ".trial-post")


def walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def stop(reason, plan):
    os.makedirs(HOME, exist_ok=True)
    open(os.path.join(HOME, "STOP"), "a").write(f"{now().isoformat()} plan {plan}: {reason}\n")
    print("STOP:", reason); sys.exit(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--response", required=True); ap.add_argument("--config")
    a = ap.parse_args()
    cfg = load_config(a.config)
    plan = json.load(open(os.path.join(HOME, "plans", a.plan + ".json")))
    r = parse_response(open(a.response, encoding="utf-8").read())
    text = json.dumps(r, default=str).lower()
    if '"error"' in text and '"_id"' not in text and '"id"' not in text:
        stop("create returned an error: " + text[:300], a.plan)
    post_id = next((d.get("_id") or d.get("id") for d in walk(r) if (d.get("_id") or d.get("id")) and "status" in d), None)
    status = next((d.get("status") for d in walk(r) if "status" in d and ("platforms" in d or "_id" in d)), None)
    if not post_id:
        stop("no post id in the response", a.plan)
    tgt = next((d for d in walk(r) if d.get("platform") == plan["platform"]), {})
    if plan["platform"] == "instagram":
        psd = tgt.get("platformSpecificData") or {}
        strat = (psd.get("trialParams") or {}).get("graduationStrategy") or tgt.get("trialGraduationStrategy")
        if strat != "MANUAL" or tgt.get("isTrialReel") is False:
            stop(f"Instagram target has no MANUAL trial proof (trialParams={psd.get('trialParams')}, "
                 f"isTrialReel={tgt.get('isTrialReel')}): it may be a FEED post. Check the app now", a.plan)
    if status in ("failed", "error"):
        stop(f"post status {status}", a.plan)
    if status in ("publishing", "pending", "processing"):
        print(f"{post_id}: still {status}; poll posts_get and re-run"); return 4
    ledger_add(cfg, {"plan": a.plan, "platform": plan["platform"], "idea": plan.get("idea"), "hook": plan.get("hook"), "post_id": post_id, "status": status or "unknown",
                     "sha256": plan["sha256"], "video": plan["video"], "when": plan["when"],
                     "trial": plan["platform"] == "instagram", "recorded": now().isoformat(),
                     "url": tgt.get("platformPostUrl")})
    print(f"OK {plan['platform']} {post_id} status={status}" + (" trial=MANUAL" if plan["platform"] == "instagram" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
