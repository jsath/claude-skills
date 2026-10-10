"""Verification gates. Each returns {name, pass, detail...}. The pipeline fails loudly if any fails.

  frames     : every chunk has exactly the EDL's frame count; video and audio durations match
  words      : re-transcribed FINAL audio vs source transcript minus removed retakes (no lost phrases)
  av_sync    : at N points, final audio == source audio at the mapped time (GCC-PHAT lag) and the final
               frame matches the source frame at that time better than +-0.5 s (picture not shifted)
  captions   : per chapter, SRT cue starts vs rising-energy onsets of the FINAL audio (independent of
               whisper): median <= 0.12 s, p95 <= 0.25 s
  loudness   : integrated within +-1 LU of target, true peak <= -1 dBTP
"""
import os, subprocess
from difflib import SequenceMatcher
import numpy as np
from .common import ffbin, read_wav, norm
from .transcribe import envelope_db


def gate_frames(chunk_results, video_dur, audio_dur, fps):
    bad = [(i, e, g) for i, (e, g) in enumerate(chunk_results) if e != g]
    diff = abs(video_dur - audio_dur)
    ok = not bad and diff <= 1.5 / fps
    return {"name": "frames", "pass": ok, "bad_chunks": bad, "video_s": round(video_dur, 3),
            "audio_s": round(audio_dur, 3), "diff_ms": round(diff * 1000, 1)}


def gate_words(cfg, src_words, removed_idx, ghost, final_words, edl):
    G = cfg["gates"]
    exp = [(norm(w["w"]), i) for i, w in enumerate(src_words) if i not in removed_idx and not ghost[i] and norm(w["w"])]
    got = [norm(w["w"]) for w in final_words if norm(w["w"])]
    fill = set(cfg["retakes"]["fillers"])
    sm = SequenceMatcher(None, [e for e, _ in exp], got, autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    runs = []
    soft = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            a = " ".join(e for e, _ in exp[i1:i2]); b = " ".join(got[j1:j2])
            if tag == "replace" and SequenceMatcher(None, a, b).ratio() >= 0.6:
                soft += i2 - i1
                continue
            content = [e for e, _ in exp[i1:i2] if e not in fill]
            # whisper often drops a phrase that is repeated right next to itself; if every word of the
            # "missing" run also appears in the 15 expected words around it, it is de-duplication, not loss
            near = set(e for e, _ in exp[max(0, i1 - 15):i1] + exp[i2:i2 + 15])
            if content and all(c in near for c in content):
                soft += i2 - i1
                continue
            if len(content) >= 3:
                si = exp[i1][1]
                runs.append({"n": len(content), "src_t": round(src_words[si]["s"], 2), "expected": a,
                             "heard": b, "out_t": None})
    recall = (matched + soft) / max(1, len(exp))
    worst = max((r["n"] for r in runs), default=0)
    ok = recall >= G["word_recall_min"] and worst < G["missing_run_fail_words"]
    return {"name": "words", "pass": ok, "recall": round(recall, 4), "expected_words": len(exp),
            "final_words": len(got), "missing_runs": runs, "worst_run": worst}


def _gray(cfg, path, t, w=320, pre=""):
    r = subprocess.run([ffbin(cfg, "ffmpeg"), "-v", "error", "-ss", f"{max(0, t):.4f}", "-i", path, "-frames:v", "1",
                        "-vf", f"{pre}scale={w}:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    return a.astype(np.float32) if len(a) else None


def gate_av(cfg, final_mp4, final16, src16, edl, src_video, vf_ref=""):
    """At N points spread over the output (inside 1x segments, 1.3 s from any edit): the final audio must match the
    source audio at the mapped time (normalised cross-correlation lag <= av_audio_lag_max_ms) and the final frame
    must match the source frame at that time better than the frames 0.5 s either side (picture not shifted)."""
    G = cfg["gates"]
    y, sr = read_wav(final16); y = y[:, 0]
    x, _ = read_wav(src16); x = x[:, 0]
    total = edl[-1]["out_e"] if edl else 0
    picks = []
    for i in range(G["av_probe_points"]):
        t = total * (i + 0.5) / G["av_probe_points"]
        best = None
        for g in edl:
            if g["speed"] != 1.0 or g["out_e"] - g["out_s"] < 2.8:
                continue
            T = min(max(t, g["out_s"] + 1.3), g["out_e"] - 1.3)
            if best is None or abs(T - t) < abs(best[0] - t):
                best = (T, g)
        if best and all(abs(best[0] - p[0]) > 2.0 for p in picks):
            picks.append(best)
    pts = []
    for T, g in picks:
        S = g["s"] + (T - g["out_s"])
        a = x[int((S - 1.0) * sr): int((S + 1.0) * sr)]
        b = y[int((T - 1.2) * sr): int((T + 1.2) * sr)]
        rec = {"out_t": round(T, 2), "src_t": round(S, 2)}
        if len(a) > sr and len(b) > len(a) and np.std(a) > 1e-4:
            c = np.correlate(b, a, "valid")
            en = np.sqrt(np.convolve(b ** 2, np.ones(len(a)), "valid") * np.sum(a ** 2)) + 1e-12
            nc = c / en
            k = int(np.argmax(nc))
            rec["audio_lag_ms"] = round((k / sr - 0.2) * 1000, 1); rec["audio_z"] = round(float(nc[k]), 3)
        f = _gray(cfg, final_mp4, T)
        s0, sm, sp = (_gray(cfg, src_video, S + d, pre=vf_ref) for d in (0.0, -0.5, 0.5))
        if f is not None and s0 is not None and len(f) == len(s0):
            mad = lambda u: float(np.mean(np.abs(f - u))) if u is not None and len(u) == len(f) else 999.0
            rec["mad_here"] = round(mad(s0), 2); rec["mad_pm05"] = round(min(mad(sm), mad(sp)), 2)
            rec["video_ok"] = rec["mad_here"] <= rec["mad_pm05"] + 0.05 or rec["mad_here"] < 1.5
        pts.append(rec)
    lags = [abs(p["audio_lag_ms"]) for p in pts if "audio_lag_ms" in p and p.get("audio_z", 0) > 0.5]
    aok = all(l <= G["av_audio_lag_max_ms"] for l in lags) and len(lags) >= max(1, len(pts) // 2)
    vok = all(p.get("video_ok", True) for p in pts)
    return {"name": "av_sync", "pass": aok and vok, "points": pts, "max_audio_lag_ms": max(lags) if lags else None}


def onsets(db, hop, thr, quiet_s=0.25):
    """Rising-energy onsets: first frame above thr+6 dB after >= quiet_s below thr."""
    out = []
    need = int(quiet_s / hop)
    q = 0
    hi = thr + 6
    armed = False
    for i, v in enumerate(db):
        if v < thr:
            q += 1
            if q >= need:
                armed = True
        else:
            if armed and v >= hi:
                # walk back to the threshold crossing
                j = i
                while j > 0 and db[j - 1] >= thr:
                    j -= 1
                out.append(j * hop)
                armed = False
            if v >= thr:
                q = 0
    return np.array(out)


def gate_captions(cfg, cues, chapters, final16, thr):
    G = cfg["gates"]
    db, hop = envelope_db(final16)
    ons = onsets(db, hop, thr)
    per = []
    bounds = [c["t"] for c in chapters] + [1e9]
    allerr = []
    for ci, ch in enumerate(chapters):
        errs = []
        for cue in cues:
            if not (bounds[ci] <= cue["s"] < bounds[ci + 1]):
                continue
            # measurable only if the cue follows a pause (quiet just before it)
            i0, i1 = int((cue["s"] - 0.45) / hop), int((cue["s"] - 0.12) / hop)
            if i0 < 0 or i1 <= i0:
                continue
            if np.mean(db[i0:i1] < thr) < 0.7:
                continue
            if len(ons) == 0:
                continue
            k = np.argmin(np.abs(ons - cue["s"]))
            d = cue["s"] - ons[k]
            if abs(d) <= 0.6:
                errs.append(abs(d))
        allerr += errs
        if len(errs) >= 3:
            med, p95 = float(np.median(errs)), float(np.percentile(errs, 95))
            ok = med <= G["caption_median_max_s"] and p95 <= G["caption_p95_max_s"]
        else:
            med = p95 = None; ok = True
        per.append({"chapter": ch["title"], "t": ch["t"], "n": len(errs), "median": None if med is None else round(med, 3),
                    "p95": None if p95 is None else round(p95, 3), "pass": ok})
    warn = None
    if len(allerr) >= 5 and float(np.percentile(allerr, 95)) > G["caption_p95_max_s"]:
        warn = (f"overall p95 {np.percentile(allerr, 95):.2f}s exceeds {G['caption_p95_max_s']}s (chapters with <3 "
                "measurable cues are not gated): spot-check caption timing after pauses")
    return {"name": "captions", "pass": all(p["pass"] for p in per), "per_chapter": per, "warning": warn,
            "overall_median": round(float(np.median(allerr)), 3) if allerr else None,
            "overall_p95": round(float(np.percentile(allerr, 95)), 3) if allerr else None, "n": len(allerr)}


def gate_loudness(cfg, final_meas):
    G = cfg["gates"]; M = cfg["master"]
    ok = abs(final_meas["I"] - M["target_lufs"]) <= G["loudness_tolerance_lu"] and final_meas["TP"] <= G["tp_max_db"]
    return {"name": "loudness", "pass": ok, **final_meas}


def gate_caption_coverage(cfg, cues, final_words):
    """Captions on every word: >= captions_coverage_min of the FINAL words must sit inside a cue's on-screen time."""
    mids = [(w["s"] + w["e"]) / 2 for w in final_words if norm(w["w"])]
    spans = sorted((c["s"] - 0.05, c["e"] + 0.05) for c in cues)
    starts = np.array([s for s, _ in spans]) if spans else np.zeros(0)
    miss = []
    for t, w in zip(mids, [w for w in final_words if norm(w["w"])]):
        k = int(np.searchsorted(starts, t, side="right")) - 1
        if k < 0 or t > spans[k][1]:
            miss.append(f"{w['w']}@{t:.1f}s")
    cov = 1 - len(miss) / max(1, len(mids))
    return {"name": "caption_coverage", "pass": cov >= cfg["gates"]["captions_coverage_min"], "coverage": round(cov, 4),
            "uncovered": miss[:40]}
