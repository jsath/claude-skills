"""Turn words + energy + retakes + screen activity into an EDL of (src_start, src_end, speed) keeps.

Every silence >= min_silence_s gets a decision, logged with its evidence:
  static  -> tighten to a natural gap (0.28 s mid-sentence, 0.40 s at a sentence end, breath kept)
  cursor  -> tighten to cursor_only_gap_s (the pointer moving, nothing else changes)
  action  -> keep the on-screen action; if longer than speedup_min_s, speed it up (1.5-3x) and play the
             final result_hold_s at 1x so the viewer sees the result land
Cuts only ever land inside measured silence (energy below the quiet threshold) or inside a removed
retake, never mid-word.
"""
import math
import numpy as np
from .transcribe import quiet_runs
from . import retakes as RT


def _pause_runs(words, db, hop, thr):
    """For each word boundary i->i+1: the longest quiet run between the two word centres."""
    runs = quiet_runs(db, thr, hop, 0.05)
    starts = np.array([r[0] for r in runs]) if runs else np.zeros(0)
    out = []
    j = 0
    for i in range(len(words) - 1):
        c0 = (words[i]["s"] + words[i]["e"]) / 2
        c1 = (words[i + 1]["s"] + words[i + 1]["e"]) / 2
        best = None
        while j < len(runs) and runs[j][1] <= c0:
            j += 1
        k = j
        while k < len(runs) and runs[k][0] < c1:
            qs, qe = max(runs[k][0], c0), min(runs[k][1], c1)
            if qe > qs and (best is None or qe - qs > best[1] - best[0]):
                best = (qs, qe)
            k += 1
        out.append(best)
    out.append(None)
    return out


def _breath_preroll(db, hop, floor, cfg, onset):
    """Seconds of lead-in to keep before a word: at least handle_before, extended over an audible breath."""
    D = cfg["deadspace"]; A = cfg["audio_detect"]
    pre = D["handle_before_word_s"]
    lim = D["max_breath_preroll_s"]
    i = int(onset / hop) - 1
    n = 0
    thr_b = floor + A["breath_above_floor_db"]
    # skip the immediate pre-roll, then see whether a breath (above floor, below speech) sits right before
    while i - n > 0 and n * hop < lim and db[i - n] > thr_b:
        n += 1
    return max(pre, min(lim, n * hop + 0.04)) if n * hop > 0.08 else pre


def build(cfg, words, db, hop, floor, thr, screen, duration, overrides=None, log=print):
    D = cfg["deadspace"]
    overrides = overrides or {}
    ghost = []
    for w in words:
        i0, i1 = int(w["s"] / hop), max(int(w["s"] / hop) + 1, int(w["e"] / hop))
        seg = db[i0:i1]
        ghost.append(bool(len(seg) == 0 or seg.max() < thr + 3.0))
    pruns = _pause_runs(words, db, hop, thr)
    pause_after = [(r[1] - r[0]) if r else 0.0 for r in pruns]
    removals = RT.detect(cfg, words, pause_after, ghost)
    keep_ids = set(overrides.get("keep_retakes", []))
    cut_ids = set(overrides.get("cut_retakes", []))
    for r in removals:
        if r["id"] in keep_ids and r["action"] == "cut":
            r["action"] = "flag"; r["why"] += " [kept by override]"
        elif r["id"] in cut_ids and r["action"] == "flag":
            r["action"] = "cut"; r["why"] += " [cut by override]"
    removed = [False] * len(words)
    for r in removals:
        if r["action"] == "cut":
            for k in range(r["i0"], r["i1"]):
                removed[k] = True
    kept = [i for i in range(len(words)) if not removed[i] and not ghost[i]]

    def speech_end(i):
        r = pruns[i]
        if r and r[0] < words[i]["e"] + 0.6:
            return min(r[0], words[i]["e"]) if r[0] < words[i]["e"] else r[0]
        return words[i]["e"]

    def speech_start(i):
        r = pruns[i - 1] if i > 0 else None
        if r and r[1] > words[i]["s"] - 0.6:
            return max(r[1], words[i]["s"]) if r[1] > words[i]["s"] else r[1]
        return words[i]["s"]

    def low_energy_point(t, rad=0.06):
        i0, i1 = max(0, int((t - rad) / hop)), int((t + rad) / hop) + 1
        seg = db[i0:i1]
        return (i0 + int(np.argmin(seg))) * hop if len(seg) else t

    cuts = []       # (s, e, reason_id)
    speeds = []     # (s, e, k)
    decisions = []

    def decide_gap(g0, g1, a_idx, b_idx, retake=None):
        return _decide_gap(cfg, cfg["deadspace"], g0, g1, a_idx, b_idx, retake)

    def _decide_gap(cfg, D, g0, g1, a_idx, b_idx, retake=None):
        L = g1 - g0
        ends_sentence = a_idx is not None and words[a_idx]["w"].rstrip().endswith((".", "?", "!"))
        target = D["gap_sentence_end_s"] if ends_sentence else D["gap_mid_sentence_s"]
        pre = _breath_preroll(db, hop, floor, cfg, g1) if b_idx is not None else 0.0
        head = max(D["handle_after_word_s"], target - pre) if a_idx is not None else 0.0
        rec = {"src_s": round(g0, 3), "src_e": round(g1, 3), "len": round(L, 3),
               "after": words[a_idx]["w"] if a_idx is not None else "(start)",
               "before": words[b_idx]["w"] if b_idx is not None else "(end)"}
        if retake is not None:
            cls = screen.classify(g0, g1) if screen else {"class": "static"}
            c0, c1 = g0 + head, g1 - pre
            if c1 - c0 > 0.02:
                cuts.append((c0, c1, retake["id"]))
            rec.update({"class": "retake", "decision": f"removed retake {retake['id']}", "removed_s": round(max(0, c1 - c0), 3),
                        "screen": cls.get("class")})
            if cls.get("class") == "action" and c1 - c0 > 0.6:
                rec["flag"] = "screen changed during the removed take: check the picture jump"
            decisions.append(rec); return
        if a_idx is None:   # head of the recording
            keep = D["head_keep_s"]
            c0, c1 = 0.0, g1 - max(pre, keep)
            if c1 > D["min_cut_s"]:
                cuts.append((c0, c1, "head")); rec.update({"class": "head", "decision": "trimmed lead-in", "removed_s": round(c1, 3)})
            else:
                rec.update({"class": "head", "decision": "kept", "removed_s": 0})
            decisions.append(rec); return
        if b_idx is None:   # tail
            c0 = g0 + D["tail_keep_s"]
            if duration - c0 > D["min_cut_s"]:
                cuts.append((c0, duration, "tail")); rec.update({"class": "tail", "decision": "trimmed run-out", "removed_s": round(duration - c0, 3)})
            else:
                rec.update({"class": "tail", "decision": "kept", "removed_s": 0})
            decisions.append(rec); return
        if L < D["min_silence_s"]:
            return
        cls = screen.classify(g0, g1) if screen else {"class": "static"}
        rec["screen"] = {k: cls[k] for k in ("motion_s", "net_frac") if k in cls}
        rec["class"] = cls["class"]
        if cls["class"] in ("static", "cursor"):
            tgt = target if cls["class"] == "static" else max(target, D["cursor_only_gap_s"])
            hd = max(D["handle_after_word_s"], tgt - pre)
            c0, c1 = g0 + hd, g1 - pre
            if c1 - c0 >= D["min_cut_s"]:
                cuts.append((c0, c1, "pause"))
                rec.update({"decision": f"tightened to {hd + pre:.2f}s", "removed_s": round(c1 - c0, 3),
                            "why": "silent, screen static" if cls["class"] == "static" else "silent, only the cursor moved"})
            else:
                rec.update({"decision": "kept (too short to cut)", "removed_s": 0})
            decisions.append(rec); return
        # action: keep the span(s), trim idle either side, speed up if long
        sa, sb = cls["spans"][0]
        sa, sb = max(sa, g0 + D["handle_after_word_s"]), min(sb, g1 - pre)
        removed_s = 0.0
        if sa - (g0 + head) >= D["min_cut_s"]:
            cuts.append((g0 + head, sa, "pause-idle")); removed_s += sa - (g0 + head)
        else:
            sa = g0 + head if sa > g0 + head else sa
        if (g1 - pre) - sb >= D["min_cut_s"]:
            cuts.append((sb, g1 - pre, "pause-idle")); removed_s += (g1 - pre) - sb
        La = sb - sa
        note = f"kept {La:.1f}s of on-screen action"
        if La > D["speedup_min_s"]:
            hold = min(D["result_hold_s"], La / 3)
            fast = La - hold
            k = fast / D["speedup_target_s"]
            k = min(D["speedup_max_factor"], max(D["speedup_min_factor"], k))
            st = D["speedup_step"]
            k = max(D["speedup_min_factor"], round(k / st) * st)
            speeds.append((sa, sb - hold, k))
            removed_s += fast - fast / k
            note += f", sped up {fast:.1f}s at {k:g}x (last {hold:.1f}s at 1x)"
        rec.update({"decision": note, "removed_s": round(removed_s, 3),
                    "why": f"silent but the screen is doing something (motion {cls['motion_s']:.1f}s, net change {cls['net_frac']*100:.2f}%)"})
        decisions.append(rec)

    # head
    if kept:
        decide_gap(0.0, speech_start(kept[0]), None, kept[0])
    for a, b in zip(kept, kept[1:]):
        rt = None
        if b - a > 1:
            rt = next((r for r in removals if r["action"] == "cut" and a < r["i0"] < b), None)
            if rt is None:
                # only ghost words between: treat as a pause
                rt = None
        if rt is not None:
            g0 = pruns[a][0] if pruns[a] else low_energy_point(words[a]["e"])
            g1 = pruns[b - 1][1] if pruns[b - 1] else low_energy_point(words[b]["s"])
            if g1 <= g0:
                g0, g1 = low_energy_point(words[a]["e"]), low_energy_point(words[b]["s"])
            decide_gap(g0, g1, a, b, retake=rt)
        else:
            if pruns[a] is None or pruns[b - 1] is None:
                continue  # no measured silence between these words: never cut
            g0, g1 = speech_end(a), speech_start(b)
            if g1 > g0:
                decide_gap(g0, g1, a, b)
    if kept:
        decide_gap(speech_end(kept[-1]), duration, kept[-1], None)
    # user overrides
    for fc in overrides.get("force_cut", []):
        cuts.append((float(fc["s"]), float(fc["e"]), fc.get("why", "override")))
    keep_ranges = [(float(a), float(b)) for a, b in overrides.get("keep_ranges", [])]
    if keep_ranges:
        cuts = [c for c in cuts if not any(c[0] < kb and c[1] > ka for ka, kb in keep_ranges)]
        # a keep range also means real time (no speed-up), e.g. a clip playing that whisper skipped
        speeds = [s_ for s_ in speeds if not any(s_[0] < kb and s_[1] > ka for ka, kb in keep_ranges)]
    return cuts, speeds, decisions, removals, ghost, pruns


def to_edl(cuts, speeds, duration, fps):
    """Keep segments on the frame grid: list of dicts {s, e, speed, frames}."""
    snap = lambda t: round(t * fps) / fps
    cuts = sorted((snap(a), snap(b)) for a, b, *_ in cuts if b > a)
    merged = []
    for a, b in cuts:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    keeps, t = [], 0.0
    end = math.floor(duration * fps) / fps
    for a, b in merged:
        if a > t:
            keeps.append((t, min(a, end)))
        t = max(t, b)
    if t < end:
        keeps.append((t, end))
    # split keeps by speed ranges
    sp = sorted((snap(a), snap(b), k) for a, b, k in speeds if snap(b) > snap(a))
    segs = []
    for a, b in keeps:
        cur = a
        for sa, sb, k in sp:
            if sb <= cur or sa >= b:
                continue
            if sa > cur:
                segs.append((cur, sa, 1.0))
            segs.append((max(sa, cur), min(sb, b), k))
            cur = min(sb, b)
        if cur < b:
            segs.append((cur, b, 1.0))
    out = []
    for a, b, k in segs:
        n = int(round((b - a) * fps))
        if n <= 0:
            continue
        if k == 1.0:
            frames = n
        else:
            frames = sum(1 for j in range(n) if (j % k) < 1)
        out.append({"s": round(a, 6), "e": round(a + n / fps, 6), "speed": k, "src_frames": n, "frames": frames})
    t = 0
    for sgm in out:
        sgm["out_s"] = t / fps
        t += sgm["frames"]
        sgm["out_e"] = t / fps
    return out


def src_to_out(edl, t):
    for g in edl:
        if g["s"] <= t < g["e"]:
            return g["out_s"] + (t - g["s"]) / g["speed"]
        if t < g["s"]:
            return g["out_s"]
    return edl[-1]["out_e"] if edl else 0.0


def out_to_src(edl, t):
    for g in edl:
        if g["out_s"] <= t < g["out_e"]:
            return g["s"] + (t - g["out_s"]) * g["speed"], g["speed"]
    return (edl[-1]["e"], 1.0) if edl else (0.0, 1.0)
