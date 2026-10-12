#!/usr/bin/env python3
"""Cut the pauses out of a talking-head take without cutting speech.

usage: tighten.py in.mov out.mp4 [--db -50] [--min-pause 0.18] [--keep 0.12] [--dry-run]
  --db         silence threshold. Keep it at -50 dB. At -38 dB consonants, word tails and
               breaths count as silence and get cut: that is what "choppy" sounds like.
  --min-pause  only pauses at least this long are shortened (0.16 to 0.22)
  --keep       seconds of each pause that stay in (0.10 to 0.13), split before/after the cut
Video and audio are cut at the same points (picture follows audio, never time-stretched).
Retakes are NOT removed here: find them in the transcript and cut them first (keep the last take).
"""
import argparse, os, re, subprocess, sys, tempfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--db", type=float, default=-50); ap.add_argument("--min-pause", type=float, default=0.18)
    ap.add_argument("--keep", type=float, default=0.12); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.src],
                               capture_output=True, text=True, check=True).stdout)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.src, "-map", "a:0",
                          "-af", f"silencedetect=noise={a.db}dB:d={a.min_pause}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    half = a.keep / 2
    keep, cur = [], 0.0
    for s, e in zip(starts, ends):
        cut0, cut1 = s + half, e - half
        if cut1 - cut0 > 0.02:
            keep.append((cur, cut0)); cur = cut1
    keep.append((cur, dur))
    keep = [(s, e) for s, e in keep if e - s > 0.02]
    removed = dur - sum(e - s for s, e in keep)
    print(f"{len(starts)} pauses >= {a.min_pause}s at {a.db} dB; {dur:.2f}s -> {dur - removed:.2f}s (removed {removed:.2f}s)")
    if a.dry_run:
        for s, e in keep:
            print(f"keep {s:8.3f} -> {e:8.3f}")
        return
    has_v = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=index",
                                 "-of", "csv=p=0", a.src], capture_output=True, text=True).stdout.strip())
    parts, labels = [], []
    for i, (s, e) in enumerate(keep):
        if has_v:
            parts.append(f"[0:v]trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={s:.4f}:end={e:.4f},asetpts=PTS-STARTPTS[a{i}]")
        labels.append((f"[v{i}]" if has_v else "") + f"[a{i}]")
    parts.append("".join(labels) + f"concat=n={len(keep)}:v={1 if has_v else 0}:a=1" + ("[v][a]" if has_v else "[a]"))
    g = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False); g.write(";\n".join(parts)); g.close()
    cmd = ["nice", "-n", "15", "ffmpeg", "-v", "error", "-y", "-i", a.src, "-filter_complex_script", g.name]
    cmd += (["-map", "[v]", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p"] if has_v else [])
    cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", a.out]
    subprocess.run(cmd, check=True); os.unlink(g.name)
    print(f"-> {a.out}  (re-transcribe this file before timing anything)")


if __name__ == "__main__":
    main()
