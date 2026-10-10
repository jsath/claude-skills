#!/usr/bin/env python3
"""Caption cues: TEXT from the script, TIMING from Whisper.

usage: make_cues.py script.txt words.json [--per-cue 2] [--fix fixmap.json] [--out DIR]
  script.txt   what was said, spelled the way it must appear on screen (names, digits)
  words.json   word stamps from use-local-whisper (transcribe.py) of the SAME audio the captions go on
  fixmap.json  optional {"cloud": "Claude"}: applied to Whisper words before matching
writes:
  cues.json      [{"text": "YOUR AI", "start": 0.02, "end": 0.40}, ...]   feed to burn_captions.py
  captions.json  [{"w": "Your", "t": 0.02}, ...]                         feed to caption_sync_gate.py
Script words Whisper missed get times interpolated from their neighbours; the count is printed.
More than 5% unmatched (and more than 2 words) means the script and the audio differ: fix the script, do not ship.
"""
import argparse, difflib, json, os, re, sys


def norm(w):
    return "".join(c for c in w.lower() if c.isalnum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script"); ap.add_argument("words")
    ap.add_argument("--per-cue", type=int, default=2)
    ap.add_argument("--fix"); ap.add_argument("--out", default=".")
    a = ap.parse_args()
    script = re.findall(r"\S+", open(a.script).read())
    words = json.load(open(a.words))
    fix = {k.lower(): v for k, v in json.load(open(a.fix)).items()} if a.fix else {}
    heard = [norm(fix.get(norm(w["w"]), w["w"])) for w in words]
    sm = difflib.SequenceMatcher(a=[norm(s) for s in script], b=heard, autojunk=False)
    t = [None] * len(script); e = [None] * len(script)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            t[blk.a + k] = words[blk.b + k]["s"]; e[blk.a + k] = words[blk.b + k]["e"]
    missing = sum(x is None for x in t)
    # interpolate gaps between known neighbours
    known = [i for i, x in enumerate(t) if x is not None]
    if not known:
        sys.exit("no script word matched the transcript: wrong audio or wrong script")
    for i in range(len(t)):
        if t[i] is None:
            lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
            if lo is None:
                t[i] = e[i] = t[hi]
            elif hi is None:
                t[i] = e[i] = e[lo]
            else:
                f = (i - lo) / (hi - lo); t[i] = e[i] = e[lo] + (t[hi] - e[lo]) * f
    cues = []
    n = max(1, a.per_cue)
    for i in range(0, len(script), n):
        g = range(i, min(i + n, len(script)))
        text = " ".join(script[j] for j in g)
        cues.append({"text": text, "start": round(t[g[0]], 3), "end": round(e[g[-1]], 3)})
    for c, nxt in zip(cues, cues[1:]):  # hold each cue until the next one, no flicker gaps under 0.4 s
        if nxt["start"] - c["end"] < 0.4:
            c["end"] = nxt["start"]
    os.makedirs(a.out, exist_ok=True)
    json.dump(cues, open(os.path.join(a.out, "cues.json"), "w"), indent=1)
    json.dump([{"w": s, "t": round(t[i], 3)} for i, s in enumerate(script)], open(os.path.join(a.out, "captions.json"), "w"), indent=1)
    pct = 100 * missing / len(script)
    print(f"{len(script)} script words, {missing} unmatched ({pct:.1f}%), {len(cues)} cues -> {a.out}/cues.json, captions.json")
    if missing > max(2, 0.05 * len(script)):
        print("WARN: >5% unmatched. Script and audio differ (retakes cut? numbers spelled out?). Fix before burning.")
        sys.exit(2)


if __name__ == "__main__":
    main()
