#!/usr/bin/env python3
"""Conform raw camera clips before any edit: optional mirror (selfie view), constant 30 fps, TV-range BT.709.

usage: conform.py OUT_DIR clip.mp4 [clip2.mp4 ...] [--mirror] [--fps 30] [--threads 4] [--dry-run]

--mirror   horizontal flip, for creators who prefer how they look in a mirror / selfie view. It runs HERE, on the raw
           camera clip, before captions, logos, screen captures or cards are added (those are never mirrored).
           Mirrored footage shows any text behind you backwards (shirt logos, signs, screens): look at a frame and
           blur, crop or reshoot. Phone and screen recordings are not mirrored unless the creator asks.
Full-range (pc) camera files are scaled to TV range; already-TV files are only tagged. Audio is copied untouched,
so audio and video stay the same length. One ffmpeg at a time, nice 15. Never overwrites the raw file.
Writes OUT_DIR/conform-manifest.jsonl: one line per clip with the ops applied.
"""
import argparse, datetime as dt, json, os, subprocess, sys

TAGS = "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"


def color_range(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_range",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return r.stdout.strip() or "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir"); ap.add_argument("clips", nargs="+")
    ap.add_argument("--mirror", action="store_true"); ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--threads", type=int, default=4); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for src in a.clips:
        out = os.path.join(a.out_dir, os.path.splitext(os.path.basename(src))[0] + ".mp4")
        if os.path.abspath(out) == os.path.abspath(src):
            sys.exit(f"refusing to overwrite the raw file {src}")
        if os.path.exists(out):
            print("exists, skipped:", out); continue
        rng = color_range(src)
        vf = (["hflip"] if a.mirror else []) + [f"fps={a.fps}"]
        if rng == "pc":
            vf.append("scale=in_range=pc:out_range=tv:in_color_matrix=bt709:out_color_matrix=bt709")
        vf += ["format=yuv420p", TAGS]
        cmd = ["nice", "-n", "15", "ffmpeg", "-v", "error", "-y", "-threads", str(a.threads), "-i", src,
               "-vf", ",".join(vf), "-color_range", "tv", "-color_primaries", "bt709", "-color_trc", "bt709",
               "-colorspace", "bt709", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-c:a", "copy",
               "-movflags", "+faststart", out]
        print(" ".join(cmd) if a.dry_run else f"conform {os.path.basename(src)} ({rng}, mirror={a.mirror})", flush=True)
        if a.dry_run:
            continue
        subprocess.run(cmd, check=True)
        with open(os.path.join(a.out_dir, "conform-manifest.jsonl"), "a") as f:
            f.write(json.dumps({"source": src, "output": out, "ops": (["hflip"] if a.mirror else []) + [f"fps{a.fps}"],
                                "color_range_in": rng, "when": dt.datetime.now().isoformat(timespec="seconds")}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
