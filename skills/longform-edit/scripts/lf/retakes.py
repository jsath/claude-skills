"""Retake / false-start / stutter / filler detection on the word list.

Output is a list of removals over WORD INDEX ranges [i0, i1) with evidence. The plan turns them into
time cuts that land in silence. Rule: when unsure, keep and flag.

Detectors
  cue      : an explicit restart cue ("let me say that again", "retake", "scratch that") spoken as its own
             phrase -> remove the abandoned attempt + the cue, keep the next take.
  restart  : a phrase P followed (within window_s) by a phrase N that re-says P's words from the top
             (same first words, P ~ prefix of N) -> remove P and anything between P and N. Keeps the LAST take.
  stutter  : an adjacent repeated n-gram ("I'll show you I'll show you the") -> remove the first copy.
  filler   : um / uh standing apart from its neighbours (separated by silence) -> remove.
"""
from difflib import SequenceMatcher
from .common import norm


def _phrases(words, pause_after, cfg):
    gap = cfg["retakes"]["phrase_gap_s"]
    out, start = [], 0
    for i, w in enumerate(words):
        end_sentence = w["w"].rstrip().endswith((".", "?", "!"))
        if i == len(words) - 1 or pause_after[i] >= gap or end_sentence:
            out.append((start, i + 1))
            start = i + 1
    return out


def _text(words, i0, i1):
    return " ".join(w["w"] for w in words[i0:i1]).strip()


def detect(cfg, words, pause_after, ghost):
    R = cfg["retakes"]
    if not R["enabled"] or not words:
        return []
    nw = [norm(w["w"]) for w in words]
    fillers = set(R["fillers"])
    phrases = _phrases(words, pause_after, cfg)
    removals = []
    removed = [False] * len(words)

    def add(kind, i0, i1, conf, why, action="cut", keep_from=None):
        if i1 <= i0:
            return
        span = words[i1 - 1]["e"] - words[i0]["s"]
        if action == "cut" and span > R["max_span_s"]:
            action = "flag"; why += f" (span {span:.1f}s > max_span_s, kept)"
        if action == "cut" and any(removed[i0:i1]):
            # overlapping an existing cut: extend only the uncovered part
            if all(removed[i0:i1]):
                return
        rec = {"kind": kind, "i0": i0, "i1": i1, "s": words[i0]["s"], "e": words[i1 - 1]["e"],
               "removed_text": _text(words, i0, i1), "confidence": conf, "why": why, "action": action,
               "before": _text(words, max(0, i0 - 10), i0), "after": _text(words, i1, min(len(words), i1 + 12))}
        removals.append(rec)
        if action == "cut":
            for k in range(i0, i1):
                removed[k] = True

    content = lambda i0, i1: [nw[k] for k in range(i0, i1) if nw[k] and nw[k] not in fillers and not ghost[k]]

    # ---- A: explicit cue phrases ----
    cues = sorted({tuple(norm(x) for x in c.split()) for c in R["cue_phrases"]}, key=len, reverse=True)
    pidx = {}  # word -> phrase index
    for pi, (a, b) in enumerate(phrases):
        for k in range(a, b):
            pidx[k] = pi
    i = 0
    while i < len(nw):
        hit = None
        for c in cues:
            if tuple(nw[i:i + len(c)]) == c:
                hit = c; break
        if not hit:
            i += 1; continue
        ci, cj = i, i + len(hit)
        pi = pidx[ci]
        a, b = phrases[pi]
        own = content(a, b)
        isolated = len(own) <= len(hit) + 4
        # next take N = first phrase starting at/after cj
        nxt = next((pj for pj in range(pi, len(phrases)) if phrases[pj][0] >= cj), None)
        if nxt is None:
            add("cue", ci, cj, "low", f"cue '{' '.join(hit)}' at end of recording", action="flag"); i = cj; continue
        Ns, Ne = phrases[nxt]
        if phrases[pi][1] > cj and not isolated:
            add("cue", ci, cj, "low", f"cue words '{' '.join(hit)}' inside a longer sentence; probably not a retake", action="flag")
            i = cj; continue
        Nw = content(Ns, Ne)
        # abandoned attempt: earliest phrase within window whose opening matches N
        best = None
        for pj in range(pi, -1, -1):
            s0, s1 = phrases[pj]
            if words[s0]["s"] < words[ci]["s"] - R["window_s"]:
                break
            Pw = content(s0, min(s1, ci))
            if not Pw or not Nw:
                continue
            L = min(len(Pw), len(Nw), 6)
            sim = SequenceMatcher(None, Pw[:L], Nw[:L]).ratio()
            if sim >= 0.5 or Pw[:2] == Nw[:2]:
                best = s0
        if best is not None and isolated:
            add("cue", best, Ns, "high", f"said '{' '.join(hit)}' then re-took the line; kept the take after the cue")
        elif isolated:
            prev = phrases[pi - 1][0] if pi > 0 and phrases[pi][0] == ci else phrases[pi][0]
            add("cue", prev, Ns, "medium", f"said '{' '.join(hit)}'; removed the sentence before it (no matching re-take found)")
        else:
            add("cue", ci, cj, "low", f"cue '{' '.join(hit)}' not isolated", action="flag")
        i = cj

    # ---- B: restarts (repeated openings) ----
    for n in range(1, len(phrases)):
        Ns, Ne = phrases[n]
        Nw = content(Ns, Ne)
        if len(Nw) < 2:
            continue
        cand = None
        for m in range(n - 1, -1, -1):
            Ps, Pe = phrases[m]
            if words[Ps]["s"] < words[Ns]["s"] - R["window_s"]:
                break
            if all(removed[Ps:Pe]):
                continue
            Pw = content(Ps, Pe)
            if len(Pw) < R["restart_min_prefix_words"]:
                continue
            k = R["restart_min_prefix_words"]
            if Pw[:k] != Nw[:k]:
                continue
            sim = SequenceMatcher(None, Pw, Nw[:len(Pw)]).ratio()
            between = n - m - 1
            frag = len(Pw) <= 4
            if frag and len(Pw) >= len(Nw):
                continue  # identical short phrases said twice ("okay so") -> not a restart
            if frag and between > 1:
                continue
            if between > 3:
                continue
            complete = words[Pe - 1]["w"].rstrip().endswith((".", "?", "!")) and len(Pw) >= 4
            need = max(R["restart_similarity"], 0.9) if complete else R["restart_similarity"]
            if sim >= need:
                conf = "high" if (sim >= 0.9 and between == 0) else "medium"
                cand = (m, sim, conf, between)  # keep scanning: earliest attempt wins
            elif sim >= R["flag_similarity"] and cand is None:
                add("restart?", Ps, Ns, "low", f"opening of this line resembles the later line (similarity {sim:.2f}); kept", action="flag")
        if cand:
            m, sim, conf, between = cand
            Ps = phrases[m][0]
            first = next((k for k in range(Ps, Ns) if not removed[k]), None)
            if first is not None:
                add("restart", first, Ns, conf,
                    f"line re-started from the top (similarity {sim:.2f}, {between} phrase(s) between); kept the later take")

    # ---- C: stutters / immediate repeats ----
    i = 0
    while i < len(nw):
        done = False
        for n in (5, 4, 3, 2, 1):
            if i + 2 * n > len(nw):
                continue
            A, B = nw[i:i + n], nw[i + n:i + 2 * n]
            if not all(A) or A != B or any(removed[i:i + 2 * n]) or any(ghost[i:i + 2 * n]):
                continue
            if words[i + n]["s"] - words[i]["s"] > 1.2 * n + 1.0:
                continue
            if n == 1 and (A[0] in R["stutter_whitelist"] or A[0] in fillers):
                continue
            sep = pause_after[i + n - 1] >= 0.08
            if n >= 2 or sep:
                add("stutter", i, i + n, "high" if n >= 2 else "medium", f"repeated {'word' if n == 1 else f'{n}-word phrase'} back-to-back; removed the first copy")
            else:
                add("stutter", i, i + n, "low", "repeated word with no gap between; too tight to cut cleanly", action="flag")
            i += n; done = True
            break
        if not done:
            i += 1

    # ---- C2: near-repeat restart inside a sentence ("these are all five of the N8N, or these are all
    # five of the automations"): a 3+ word run said again within 3 words -> drop the first copy + the
    # abandoned words between.
    for i in range(len(nw)):
        if removed[i] or ghost[i] or not nw[i]:
            continue
        for n in (6, 5, 4, 3):
            A = nw[i:i + n]
            if len(A) < n or not all(A) or sum(1 for x in A if x not in fillers) < 3:
                continue
            hit = None
            for j in range(i + n + 1, min(len(nw) - n, i + n + 3) + 1):
                if nw[j:j + n] == A:
                    hit = j; break
            if hit is None or any(removed[i:hit]):
                continue
            # parallel phrasing ("all of my guides, all of my tips") is NOT a retake: require a correction
            # marker between the copies and no sentence break
            mid = nw[i + n:hit]
            marker = any(m in fillers or m in ("or", "sorry", "actually", "wait", "no", "mean") for m in mid)
            broke = any(words[k]["w"].rstrip().endswith((".", "?", "!")) for k in range(i, hit))
            if not marker or broke:
                continue
            if words[hit]["s"] - words[i]["s"] > 1.0 * n + 3.0:
                continue
            # "the yearly subscription for X, or the lifetime subscription for X": the corrected words sit
            # BEFORE the repeated run. Words after the last marker ("the lifetime") replace the same number
            # of words before the first copy ("the yearly"), so cut from there up to and including the marker.
            mk = max(k for k in range(i + n, hit) if nw[k] in fillers or nw[k] in ("or", "sorry", "actually", "wait", "no", "mean"))
            x2 = hit - (mk + 1)
            start, end = i, hit
            if 0 < x2 <= 3 and i - x2 >= 0 and not any(removed[i - x2:i]):
                start, end = i - x2, mk + 1
            add("restart", start, end, "high",
                f"self-correction: '{' '.join(nw[i:i+n])}' said twice around '{nw[mk]}'; kept the corrected version")
            break

    # ---- D: fillers ----
    if R["remove_fillers"]:
        for i, w in enumerate(nw):
            if w in fillers and not removed[i]:
                before = pause_after[i - 1] if i > 0 else 1.0
                after = pause_after[i]
                if before >= 0.08 or after >= 0.08:
                    add("filler", i, i + 1, "high", f"filler '{words[i]['w']}' separated by silence")
                else:
                    add("filler", i, i + 1, "low", f"filler '{words[i]['w']}' glued to the next word; kept", action="flag")
    removals.sort(key=lambda r: (r["i0"], r["i1"]))
    for k, r in enumerate(removals):
        r["id"] = f"R{k+1:02d}"
    return removals
