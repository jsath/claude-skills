#!/usr/bin/env python3
"""Find the camera card, copy every clip off it, prove the copies, check audio == video.

usage:
  ingest.py find                                   list mounted cards that hold camera clips
  ingest.py copy --dest DIR [--src DIR] [--since YYYY-MM-DD] [--only-new]
  ingest.py check --dest DIR                       A/V length check on copies already in DIR/raw

copy:
  - reads the card, never writes to it, never deletes from it
  - copies video clips (MP4/MOV) and mic backup audio (WAV) into DIR/raw/<card-folder>/, skipping proxies
    (LRF, THM, SRT sidecars stay on the card)
  - a file already in DIR with the same size is skipped (safe to re-run after an interruption)
  - every copy is size-verified against the card; a mismatch is re-copied once, then reported
  - writes DIR/manifest.json (source, dest, bytes, duration_video, duration_audio, av_diff, created) and
    DIR/durations.tsv; exits 1 if any copy failed or any clip's audio differs from its video by > 0.10 s
Environment:
  INGEST_CARD_GLOBS   extra mount globs to search (colon separated), e.g. "/Volumes/*:/media/$USER/*"
Needs ffprobe on PATH.
"""
import argparse, datetime as dt, glob, json, os, shutil, subprocess, sys

VIDEO = (".mp4", ".mov")
AUDIO = (".wav",)
SKIP = (".lrf", ".thm", ".srt", ".lrv")
MOUNTS = ["/Volumes/*", "/media/*/*", "/run/media/*/*", "/mnt/*"]
AV_TOL = 0.10


def mounts():
    globs = MOUNTS + [g for g in os.environ.get("INGEST_CARD_GLOBS", "").split(":") if g]
    seen = []
    for g in globs:
        for m in glob.glob(os.path.expandvars(g)):
            if os.path.isdir(m) and m not in seen and not m.startswith("/Volumes/Macintosh HD"):
                seen.append(m)
    return seen


def clip_dirs(root):
    """Folders on a card that hold clips: DCIM/* for cameras, plus any folder with WAVs (wireless mic backups)."""
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        if d.count(os.sep) - root.count(os.sep) >= 3:
            dirs[:] = []
        clips = [f for f in files if f.lower().endswith(VIDEO + AUDIO) and not f.startswith("._")]
        if clips:
            size = sum(os.path.getsize(os.path.join(d, f)) for f in clips)
            out.append({"dir": d, "clips": len(clips), "bytes": size,
                        "first": min(clips), "last": max(clips)})
    return out


def probe(path):
    def dur(sel):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", "stream=duration",
                            "-of", "csv=p=0", path], capture_output=True, text=True)
        try:
            return round(float(r.stdout.strip().splitlines()[0]), 3)
        except (ValueError, IndexError):
            return None
    return dur("v:0"), dur("a:0")


def cmd_find(_):
    found = False
    for m in mounts():
        for c in clip_dirs(m):
            found = True
            print(f"{c['dir']}\t{c['clips']} clips\t{c['bytes'] / 1e9:.2f} GB\t{c['first']} .. {c['last']}")
    if not found:
        print("no card with camera clips is mounted (plug it in, or set INGEST_CARD_GLOBS)")
        return 2
    return 0


def copy_one(src, dst):
    for attempt in (1, 2):
        shutil.copy2(src, dst + ".part")
        os.replace(dst + ".part", dst)
        if os.path.getsize(dst) == os.path.getsize(src):
            return True
    return False


def check(dest, rows):
    bad = []
    with open(os.path.join(dest, "durations.tsv"), "w") as f:
        f.write("file\tvideo_s\taudio_s\tdiff_s\tstatus\n")
        for r in rows:
            if r["dest"].lower().endswith(AUDIO):
                r["duration_audio"] = probe(r["dest"])[1]
                f.write(f"{os.path.basename(r['dest'])}\t\t{r['duration_audio']}\t\tmic-backup\n")
                continue
            v, a = probe(r["dest"])
            r["duration_video"], r["duration_audio"] = v, a
            diff = round(abs(v - a), 3) if (v is not None and a is not None) else None
            r["av_diff"] = diff
            st = "OK" if diff is not None and diff <= AV_TOL else ("NO AUDIO" if a is None else "AV MISMATCH")
            if st != "OK":
                bad.append(f"{os.path.basename(r['dest'])}: {st} (video {v}, audio {a})")
            f.write(f"{os.path.basename(r['dest'])}\t{v}\t{a}\t{diff}\t{st}\n")
    return bad


def cmd_copy(a):
    src = a.src
    if not src:
        cands = [c for m in mounts() for c in clip_dirs(m)]
        if len(cands) != 1:
            for c in cands:
                print("candidate:", c["dir"], c["clips"], "clips")
            sys.exit("pass --src: " + ("no card found" if not cands else "more than one clip folder"))
        src = cands[0]["dir"]
    raw = os.path.join(a.dest, "raw", os.path.basename(src.rstrip("/")))
    os.makedirs(raw, exist_ok=True)
    free = shutil.disk_usage(a.dest).free
    files = sorted(f for f in os.listdir(src)
                   if f.lower().endswith(VIDEO + AUDIO) and not f.lower().endswith(SKIP) and not f.startswith("._"))
    if a.since:
        cut = dt.datetime.fromisoformat(a.since).timestamp()
        files = [f for f in files if os.path.getmtime(os.path.join(src, f)) >= cut]
    need = sum(os.path.getsize(os.path.join(src, f)) for f in files)
    print(f"{len(files)} clips, {need / 1e9:.2f} GB from {src} -> {raw} ({free / 1e9:.1f} GB free)")
    if need > free * 0.9:
        sys.exit("not enough free disk: free space first, never delete from the card")
    rows, failed = [], []
    man_path = os.path.join(a.dest, "manifest.json")
    old = {r["dest"]: r for r in json.load(open(man_path))} if os.path.exists(man_path) else {}
    for i, f in enumerate(files, 1):
        s, d = os.path.join(src, f), os.path.join(raw, f)
        if os.path.exists(d) and os.path.getsize(d) == os.path.getsize(s):
            if a.only_new:
                continue
            ok = True
        else:
            ok = copy_one(s, d)
        print(f"[{i}/{len(files)}] {f} {'OK' if ok else 'SIZE MISMATCH'}", flush=True)
        if not ok:
            failed.append(f)
        rows.append({**old.get(d, {}), "source": s, "dest": d, "bytes": os.path.getsize(s),
                     "created": dt.datetime.fromtimestamp(os.path.getmtime(s)).isoformat(timespec="seconds")})
    bad = check(a.dest, rows)
    json.dump(rows, open(man_path, "w"), indent=1)
    print(f"copied + verified {len(rows) - len(failed)}/{len(rows)}; A/V problems: {len(bad)}")
    for b in failed:
        print("FAILED COPY", b)
    for b in bad:
        print("AV", b)
    print("card untouched. Eject only after this says 0 failed: scripts/eject.sh", src)
    return 1 if failed or bad else 0


def cmd_check(a):
    rows = [{"dest": p} for p in sorted(glob.glob(os.path.join(a.dest, "raw", "*", "*")))
            if p.lower().endswith(VIDEO + AUDIO)]
    bad = check(a.dest, rows)
    for b in bad:
        print("AV", b)
    print(f"{len(rows)} files checked, {len(bad)} problems")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find")
    c = sub.add_parser("copy"); c.add_argument("--dest", required=True); c.add_argument("--src")
    c.add_argument("--since"); c.add_argument("--only-new", action="store_true")
    k = sub.add_parser("check"); k.add_argument("--dest", required=True)
    a = ap.parse_args()
    return {"find": cmd_find, "copy": cmd_copy, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
