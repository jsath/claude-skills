#!/usr/bin/env python3
"""Short-form QA gates that catch what viewers swipe away on: no face in frame 1, dead air at clip joins,
audio and video of different lengths, dashes in captions.

usage: reel_qa.py final.mp4 [--words final.words.json] [--joins joins.json] [--cues cues.json]
                  [--yunet face_detection_yunet_2023mar.onnx] [--json QA.reel.json]

Gates (exit 1 if any FAILS; SKIP lines say what to check by eye instead):
  av_length      video and audio stream durations within one frame (1/30 s)
  face_first     a face in at least half of the frames in the first 0.3 s, face box >= 15% of frame height
                 (a small thumbnail of you inside a graphic does not count). Needs OpenCV + the YuNet model
                 (see face_box.py for the download line). No OpenCV: SKIP, open frame 1 and look.
  dead_air       from a re-transcription of the FINAL render (use-local-whisper): no gap between words longer
                 than 0.25 s within 0.3 s of a join, or longer than 0.35 s anywhere
  join_envelope  the mixed audio itself (mono 16 kHz, 20 ms RMS): no quiet run below -36 dBFS longer than 0.25 s
                 within 0.5 s of a join, or longer than 0.35 s anywhere inside speech (lead-in and tail ignored).
                 Whisper timestamps drift up to 0.3 s at pauses, so dead_air alone misses room-tone holes
                 at joins. Tune --quiet-db to your room: room tone usually sits 15+ dB under speech.
  dashes         no em dash and no spaced en dash in any caption cue
joins.json: the join times in the FINAL timeline, in seconds: [1.84, 6.20, 11.05]. Write it when you concat.
"""
import argparse, array, json, math, os, subprocess, sys

QUIET_DB, WIN, MAX_JOIN, MAX_ANY, REACH = -36.0, 0.02, 0.25, 0.35, 0.5


def dur(path, sel):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "stream=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def gate_av(path):
    v, a = dur(path, "v:0"), dur(path, "a:0")
    if v is None or a is None:
        return "FAIL", f"missing stream (video {v}, audio {a})"
    d = abs(v - a)
    return ("PASS" if d <= 1 / 30 + 1e-6 else "FAIL"), f"video {v:.3f} s, audio {a:.3f} s, diff {d:.3f} s"


def envelope_db(path, sr=16000, win=WIN):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-threads", "4", "-i", path, "-vn", "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x = array.array("h"); x.frombytes(pcm[: len(pcm) // 2 * 2])
    if sys.byteorder == "big":
        x.byteswap()
    n = int(sr * win); out = []
    for i in range(0, len(x) - n + 1, n):
        s = sum(v * v for v in x[i:i + n]) / n
        out.append(20 * math.log10(max(math.sqrt(s) / 32768.0, 1e-6)))
    return out


def quiet_runs(db, quiet, win=WIN):
    loud = [i for i, v in enumerate(db) if v >= quiet]
    if not loud:
        return None
    runs, start = [], None
    for i in range(loud[0], loud[-1] + 1):
        if db[i] < quiet and start is None:
            start = i
        elif db[i] >= quiet and start is not None:
            runs.append((start * win, i * win)); start = None
    return runs


def gate_envelope(path, joins, quiet):
    try:
        runs = quiet_runs(envelope_db(path), quiet)
    except subprocess.CalledProcessError:
        return "FAIL", "could not decode the audio (no audio stream?)"
    if runs is None:
        return "FAIL", f"no audio above {quiet:.0f} dBFS (silent render?)"
    p = []
    for a, b in runs:
        d = b - a
        near = [j for j in joins if a - REACH <= j <= b + REACH]
        if near and d > MAX_JOIN + 1e-9:
            p.append(f"{d:.2f} s quiet at {a:.2f} s, next to the {near[0]:.2f} s join (max {MAX_JOIN})")
        elif d > MAX_ANY + 1e-9:
            p.append(f"{d:.2f} s quiet at {a:.2f} s inside speech (max {MAX_ANY})")
    note = "" if joins else " (no joins file: only the 0.35 s bar applied)"
    return ("FAIL" if p else "PASS"), ("; ".join(p) or f"{len(runs)} pauses, all short") + note


def gate_dead_air(words, joins):
    p = []
    for a, b in zip(words, words[1:]):
        end = a.get("e", a["s"]); gap = b["s"] - end
        near = any(end - 0.3 <= j <= b["s"] + 0.3 for j in joins)
        lim = MAX_JOIN if near else MAX_ANY
        if gap > lim:
            p.append(f"{gap:.2f} s after '{a['w']}' at {end:.2f} s{' (join)' if near else ''}")
    return ("FAIL" if p else "PASS"), "; ".join(p) or f"{len(words)} words, no long gaps"


def gate_face_first(path, model):
    try:
        import cv2
    except ImportError:
        return "SKIP", "OpenCV not installed: open frame 1 and confirm your face is on screen"
    if not model or not os.path.exists(model):
        return "SKIP", "no YuNet model (--yunet): open frame 1 and confirm your face is on screen"
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = max(1, int(round(0.3 * fps))); hits = 0; det = None
    for i in range(n):
        ok, fr = cap.read()
        if not ok:
            break
        h, w = fr.shape[:2]
        if det is None:
            det = cv2.FaceDetectorYN.create(model, "", (w, h), 0.7)
        _, faces = det.detect(fr)
        if faces is not None and any(f[3] / h >= 0.15 for f in faces):
            hits += 1
    if hits * 2 >= n and hits > 0:
        return "PASS", f"face in {hits}/{n} frames of the first 0.3 s"
    return "FAIL", f"face in {hits}/{n} frames of the first 0.3 s: open on your face, never a graphic"


def gate_dashes(cues):
    bad = [c["text"] for c in cues if "\u2014" in c.get("text", "") or " \u2013 " in c.get("text", "")]
    return ("FAIL" if bad else "PASS"), ("; ".join(bad[:5]) or f"{len(cues)} cues clean")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--words"); ap.add_argument("--joins"); ap.add_argument("--cues")
    ap.add_argument("--yunet"); ap.add_argument("--quiet-db", type=float, default=QUIET_DB); ap.add_argument("--json")
    a = ap.parse_args()
    joins = json.load(open(a.joins)) if a.joins else []
    res = {"av_length": gate_av(a.video), "face_first": gate_face_first(a.video, a.yunet),
           "join_envelope": gate_envelope(a.video, joins, a.quiet_db)}
    res["dead_air"] = gate_dead_air(json.load(open(a.words)), joins) if a.words else \
        ("SKIP", "no --words: re-transcribe the final render and pass final.words.json")
    if a.cues:
        res["dashes"] = gate_dashes(json.load(open(a.cues)))
    for k, (st, msg) in res.items():
        print(f"{k:<14} {st:<4} {msg}")
    failed = [k for k, (st, _) in res.items() if st == "FAIL"]
    print("REEL QA PASS" if not failed else "REEL QA FAIL: " + ", ".join(failed))
    if a.json:
        json.dump({k: {"status": s, "detail": m} for k, (s, m) in res.items()} | {"pass": not failed},
                  open(a.json, "w"), indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
