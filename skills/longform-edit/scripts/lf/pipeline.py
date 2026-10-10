"""longform-edit pipeline: ingest -> transcribe -> screen activity -> plan -> render -> master -> re-transcribe FINAL
-> SRT/chapters/PUBLISH.md/sheets -> gates -> REVIEW.md. Every stage caches into <out>/work so a re-run after an
overrides.json edit only re-plans and re-renders."""
import argparse, csv, glob, hashlib, json, os, re, shutil, sys, time
import numpy as np
from . import common
from .common import LOG, expand, load_config, probe, extract_audio, read_wav, save_json, load_json, fmt_ts
from . import transcribe as TR, plan as PL, render as RD, verify as VF, publish as PB

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".m4v", ".webm")
AUDIO_EXT = (".wav", ".m4a", ".mp3", ".aac", ".flac")


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "video"


def parse(argv):
    ap = argparse.ArgumentParser(prog="longform_edit.py", description="Automatic long-form edit: retakes out, dead space "
                                 "tightened, voice mastered to -14 LUFS, SRT from the FINAL audio, chapters, QA gates.")
    ap.add_argument("inputs", nargs="*", help="a folder of raws (inbox/<slug>/) or a video file; none = every inbox folder without a REVIEW.md")
    ap.add_argument("--config", help="extra config json, deep-merged over config.example.json")
    ap.add_argument("--slug"); ap.add_argument("--out", help="output folder (default <outbox>/<slug>)")
    ap.add_argument("--mic", help="separate voice recording, synced to the video by audio cross-correlation")
    ap.add_argument("--words", help="use this words.json ([{w,s,e,p}]) for the SOURCE instead of running whisper")
    ap.add_argument("--kind", choices=["auto", "screen", "camera"], default=None,
                    help="footage kind: screen recordings keep silent on-screen action, camera footage treats every silence as idle")
    ap.add_argument("--plan-only", action="store_true", help="cut plan + REVIEW.md only, no render")
    ap.add_argument("--no-llm", action="store_true", help="do not call the claude CLI for titles/chapters")
    ap.add_argument("--redo", choices=["all", "plan"], help="drop cached work (all) or just the plan")
    ap.add_argument("--burn-captions", action="store_true",
                    help="also burn 2-5 word captions into the video (needs ffmpeg built with libass)")
    ap.add_argument("--keep-work", action="store_true", help="keep <out>/work after a passing run (default: delete big intermediates)")
    return ap.parse_args(argv)


def find_inputs(folder):
    files = sorted(glob.glob(os.path.join(folder, "*")))
    vids = [f for f in files if f.lower().endswith(VIDEO_EXT)]
    auds = [f for f in files if f.lower().endswith(AUDIO_EXT)]
    if not vids:
        raise SystemExit(f"no video file in {folder} (looked for {', '.join(VIDEO_EXT)})")
    if len(vids) > 1:
        LOG(f"  {len(vids)} videos in the folder: using the largest; pass a file to choose")
    return max(vids, key=os.path.getsize), (auds[0] if len(auds) == 1 else None)


def gcc_offset(cfg, ref_wav, trk_wav, max_lag_s):
    """Seconds to ADD to a reference time to get the same moment in the track (GCC-PHAT on a speech window)."""
    a, sr = read_wav(ref_wav); b, _ = read_wav(trk_wav)
    a, b = a[:, 0], b[:, 0]
    W = int(min(cfg["ingest"]["sync_window_s"], len(a) / sr - 1) * sr)
    hop = sr
    best, s0 = -1, 0
    for s in range(0, max(1, len(a) - W), hop * 5):             # the loudest window is the most distinctive
        e = float(np.sum(a[s:s + W] ** 2))
        if e > best:
            best, s0 = e, s
    ref = a[s0:s0 + W]
    m = int(max_lag_s * sr)
    trk = b[max(0, s0 - m): s0 + W + m]
    pad = s0 - max(0, s0 - m)
    n = len(ref) + len(trk)
    nfft = 1 << (n - 1).bit_length()
    X = np.fft.rfft(trk, nfft) * np.conj(np.fft.rfft(ref, nfft))
    X /= np.abs(X) + 1e-9
    cc = np.fft.irfft(X, nfft)[: len(trk) - len(ref) + 1]
    k = int(np.argmax(cc))
    z = float((cc[k] - cc.mean()) / (cc.std() + 1e-12))
    return (k - pad) / sr, z


def write_csv(path, decisions):
    keys = ["src_s", "src_e", "out_t", "len", "class", "decision", "removed_s", "after", "before", "why", "flag"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for d in decisions:
            w.writerow([d.get(k, "") for k in keys])


def cell(s, n=220):
    s = str(s).replace("|", "/").replace("\n", " ")
    return s if len(s) <= n else s[:n] + "..."


def main(argv=None):
    a = parse(argv if argv is not None else sys.argv[1:])
    base = load_config([a.config])
    inputs = a.inputs
    if not inputs:
        inbox, outbox = expand(base["paths"]["inbox"]), expand(base["paths"]["outbox"])
        inputs = [d for d in sorted(glob.glob(os.path.join(inbox, "*"))) if os.path.isdir(d)
                  and not os.path.exists(os.path.join(outbox, os.path.basename(d), "REVIEW.md"))]
        if not inputs:
            print(f"nothing to do: no folder in {inbox} without a REVIEW.md in {outbox}")
            return 0
    rc = 0
    for inp in inputs:
        rc = max(rc, edit(a, expand(inp)))
    return rc


def edit(a, inp):
    t_start = time.time()
    cfg = load_config([os.path.join(inp, "config.json") if os.path.isdir(inp) else None, a.config])
    if a.no_llm:
        cfg["publish"]["use_claude_cli"] = False
    if os.path.isdir(inp):
        video, mic = find_inputs(inp)
        slug = a.slug or slugify(os.path.basename(inp.rstrip("/")))
    else:
        video, mic = inp, None
        slug = a.slug or slugify(os.path.splitext(os.path.basename(inp))[0])
    mic = expand(a.mic) if a.mic else mic
    out = expand(a.out) if a.out else os.path.join(expand(cfg["paths"]["outbox"]), slug)
    work = os.path.join(out, "work")
    if a.redo == "all" and os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)
    LOG.path, LOG.t0 = os.path.join(out, "run.log"), t_start
    if a.redo == "plan" and os.path.exists(os.path.join(work, "plan.json")):
        os.remove(os.path.join(work, "plan.json"))
    ov_p = os.path.join(out, "overrides.json")
    overrides = load_json(ov_p) if os.path.exists(ov_p) else {}
    T = {}

    # ---- 1 ingest ----
    t = time.time(); LOG("== ingest")
    info = probe(cfg, video)
    if not info["video"]:
        raise SystemExit(f"{video} has no video stream")
    duration = info["duration"]
    v = info["video"]
    LOG(f"  video {os.path.basename(video)} {duration:.1f}s {v['width']}x{v['height']} {v['codec']} {v['avg_fps']:.2f} fps")
    src16, src48 = os.path.join(work, "src16.wav"), os.path.join(work, "src48.wav")
    sync = None
    if mic:
        if not info["audio"]:
            raise SystemExit("--mic needs the video to have its own (scratch) audio to sync against")
        ref16 = os.path.join(work, "video16.wav")
        if not os.path.exists(ref16):
            extract_audio(cfg, video, ref16, 16000)
        mic_raw = os.path.join(work, "mic16_raw.wav")
        if not os.path.exists(mic_raw):
            extract_audio(cfg, mic, mic_raw, 16000)
        off, z = gcc_offset(cfg, ref16, mic_raw, cfg["ingest"]["sync_search_s"])
        sync = {"mic": mic, "offset_s": round(off, 4), "confidence_z": round(z, 1)}
        LOG(f"  mic {os.path.basename(mic)} synced: offset {off * 1000:+.1f} ms, confidence z={z:.1f}")
        if z < cfg["ingest"]["sync_min_confidence"]:
            raise SystemExit(f"mic sync not confident (z={z:.1f} < {cfg['ingest']['sync_min_confidence']}): "
                             "clap once at the start of the take, or drop the separate mic")
        voice_src, voice_off = mic, off
    else:
        if not info["audio"]:
            raise SystemExit("the video has no audio and no --mic was given")
        voice_src, voice_off = video, 0.0
    if not os.path.exists(src16):
        extract_audio(cfg, voice_src, src16, 16000, offset=voice_off, duration=duration)
    if not os.path.exists(src48):
        extract_audio(cfg, voice_src, src48, 48000, offset=voice_off, duration=duration)
    T["ingest"] = round(time.time() - t, 1)

    # ---- 2 transcribe source ----
    t = time.time(); LOG("== transcribe")
    if a.words:
        words = load_json(expand(a.words))
    else:
        words = TR.transcribe(cfg, src16, os.path.join(work, "words_src"))
    if not words:
        raise SystemExit("transcription is empty: is there speech in the audio?")
    db, hop = TR.envelope_db(src16, cfg["audio_detect"]["hop_ms"])
    floor, thr = TR.quiet_threshold(cfg, db)
    LOG(f"  {len(words)} words; noise floor {floor:.1f} dB, quiet threshold {thr:.1f} dB")
    T["transcribe"] = round(time.time() - t, 1)

    # ---- 3 screen activity ----
    t = time.time(); LOG("== screen")
    kind = a.kind or cfg["deadspace"]["kind"]
    if kind == "auto" and re.search(cfg["ingest"]["camera_name_regex"], os.path.basename(video), re.I):
        kind = "camera"
    try:
        from .screen import ScreenActivity
        scr = ScreenActivity(cfg, video, work, kind)
        scr.run()
    except ImportError:
        LOG("  WARNING: opencv not installed: every silence treated as idle (pip install opencv-python-headless)")
        scr = None
    LOG(f"  footage kind: {scr.kind if scr else 'unknown (no opencv)'}")
    T["screen"] = round(time.time() - t, 1)

    # ---- 4 plan ----
    t = time.time(); LOG("== plan")
    fps = RD.output_fps(cfg, info)
    cfg["_fps_str"] = RD.fps_str(fps)
    cuts, speeds, decisions, removals, ghost, _ = PL.build(cfg, words, db, hop, floor, thr, scr, duration, overrides)
    edl = PL.to_edl(cuts, speeds, duration, fps)
    for d in decisions:
        d["out_t"] = round(PL.src_to_out(edl, d["src_s"]), 2)
    for r in removals:
        r["out_t"] = round(PL.src_to_out(edl, r["s"]), 2)
    final_dur = edl[-1]["out_e"] if edl else 0
    removed_idx = set()
    for r in removals:
        if r["action"] == "cut":
            removed_idx.update(range(r["i0"], r["i1"]))
    for fc in overrides.get("force_cut", []):     # words a human force-cut are removed on purpose, not lost
        removed_idx.update(i for i, w in enumerate(words) if float(fc["s"]) <= (w["s"] + w["e"]) / 2 <= float(fc["e"]))
    save_json(os.path.join(work, "plan.json"), {"edl": edl, "fps": fps})
    save_json(os.path.join(out, "decisions.json"), {"decisions": decisions, "removals": removals})
    write_csv(os.path.join(out, "decisions.csv"), decisions)
    n_cut = sum(1 for r in removals if r["action"] == "cut")
    LOG(f"  {duration:.1f}s -> {final_dur:.1f}s ({(1 - final_dur / duration) * 100:.1f}% removed); "
        f"{n_cut} removals, {len(removals) - n_cut} flagged, {len(speeds)} speed-ups")
    T["plan"] = round(time.time() - t, 1)
    ctx = dict(cfg=cfg, out=out, slug=slug, video=video, sync=sync, scr=scr, removals=removals, decisions=decisions,
               edl=edl, fps=fps, duration=duration, final_dur=final_dur, T=T, t_start=t_start)
    if a.plan_only:
        write_review(ctx, None, [], None, plan_only=True)
        LOG(f"plan only: see {os.path.join(out, 'REVIEW.md')}")
        return 0

    # ---- 5 render + master ----
    t = time.time(); LOG("== render")
    edl_hash = hashlib.sha1(json.dumps(edl, sort_keys=True).encode()).hexdigest()[:10]
    stamp = os.path.join(work, "edl_hash.txt")
    if not os.path.exists(stamp) or open(stamp).read() != edl_hash:
        for f in ("audio_edit.wav", "audio_master.wav", "video_edit.mp4", "final16.wav", "words_final.json", "master.json", "chunk_res.json"):
            if os.path.exists(os.path.join(work, f)):
                os.remove(os.path.join(work, f))
        for p in glob.glob(os.path.join(work, "chunks", "*.mp4")):
            os.remove(p)
    vid = os.path.join(work, "video_edit.mp4")
    cr_p = os.path.join(work, "chunk_res.json")
    if os.path.exists(vid) and os.path.exists(cr_p):
        chunk_res = load_json(cr_p)
    else:
        vid, chunk_res = RD.render_video(cfg, video, edl, work, fps)
        save_json(cr_p, chunk_res)
    aud = os.path.join(work, "audio_edit.wav")
    if not os.path.exists(aud):
        aud = RD.assemble_audio(cfg, src48, edl, fps, work)
    mj = os.path.join(work, "master.json")
    if os.path.exists(mj):
        mres, master = load_json(mj), os.path.join(work, "audio_master.wav")
    else:
        master, mres = RD.master_audio(cfg, aud, floor, work)
        mres["before_raw"], mres["before_edit"] = RD.ebur128(cfg, src48), RD.ebur128(cfg, aud)
        save_json(mj, mres)
    with open(stamp, "w") as f:
        f.write(edl_hash)
    LOG(f"  loudness raw I={mres['before_raw']['I']} -> final I={mres['final']['I']} LUFS, TP={mres['final']['TP']} dBTP")
    T["render"] = round(time.time() - t, 1)

    # ---- 6 re-transcribe the FINAL audio (the SRT never comes from the source transcript) ----
    t = time.time(); LOG("== final-transcribe")
    f16 = os.path.join(work, "final16.wav")
    if not os.path.exists(f16):
        extract_audio(cfg, master, f16, 16000)
    fwords = PB.apply_word_fixes(cfg, TR.transcribe(cfg, f16, os.path.join(work, "words_final")))
    LOG(f"  {len(fwords)} words in the final")
    T["final_transcribe"] = round(time.time() - t, 1)

    # ---- 7 publish package ----
    t = time.time(); LOG("== publish")
    cues = PB.build_cues(cfg, fwords)
    snap = PB.snap_cue_starts(cfg, cues, f16, work)
    srt = os.path.join(out, f"{slug}.srt")
    PB.write_srt(cues, srt)
    hints = {"screen": [PL.src_to_out(edl, x) for x in (scr.big_changes() if scr else [])],
             "pauses": [d["out_t"] for d in decisions if d.get("len", 0) >= 1.2 and d.get("class") in ("static", "cursor")]}
    cands = PB.chapter_candidates(cfg, fwords, hints)
    chosen = PB.pick_chapters(cfg, cands, final_dur)
    chapters = [{"t": round(c["t"], 2) if i else 0.0, "title": PB.heuristic_title(c.get("lead", ""))} for i, c in enumerate(chosen)]
    pkg_p = os.path.join(work, f"llm_{edl_hash}.json")
    pkg = load_json(pkg_p) if os.path.exists(pkg_p) else None
    if pkg is None and cfg["publish"]["use_claude_cli"]:
        LOG("  asking the claude CLI for chapter titles + description ...")
        pkg = PB.llm_package(cfg, fwords, chapters, cands, final_dur, work)
        if pkg:
            save_json(pkg_p, pkg)
    if pkg and pkg.get("chapters"):
        chapters = [{"t": round(c["t"], 2), "title": c["title"]} for c in pkg["chapters"]]
    chapters[0]["t"] = 0.0
    if not PB.youtube_chapters_ok(chapters, final_dur):
        LOG("  WARNING: chapters fail YouTube rules (>= 3, first at 0:00, each >= 10 s)")
    with open(os.path.join(out, "chapters.txt"), "w") as f:
        f.write("\n".join(f"{fmt_ts(c['t'])} {c['title']}" for c in chapters) + "\n")
    meta = os.path.join(work, "chapters.ffmeta")
    PB.write_ffmeta(chapters, final_dur, meta, slug)
    final_mp4 = os.path.join(out, f"{slug}.mp4")
    RD.mux(cfg, vid, master, final_mp4, meta)
    thumbs = PB.thumbnails(cfg, final_mp4, final_dur, edl, os.path.join(out, "thumbs"))
    sheet = PB.contact_sheet(cfg, final_mp4, final_dur, os.path.join(out, "contact-sheet.jpg"),
                             cfg["publish"]["contact_cols"], cfg["publish"]["contact_rows"],
                             title=f"{slug}  final {fmt_ts(final_dur)}  (raw {fmt_ts(duration)})")
    ev = [(r["out_t"], f"{r['id']} {r['kind']}") for r in removals if r["action"] == "cut"]
    ev += [(g["out_s"], f"{g['speed']:g}x speed-up") for g in edl if g["speed"] != 1.0]
    csheet = PB.cuts_sheet(cfg, final_mp4, sorted(ev), os.path.join(out, "cuts-sheet.jpg"))
    flags_extra = [f"{fmt_ts(d['out_t'])}: {d['flag']}" for d in decisions if d.get("flag")]
    PB.write_publish(cfg, os.path.join(out, "PUBLISH.md"), slug, chapters, pkg, fwords, final_dur, flags_extra)
    burn_note = None
    if a.burn_captions or cfg["publish"]["burn_captions"]:
        burn_note = burn_captions(cfg, fwords, f16, work, final_mp4, slug, out)
        LOG("  burn-in:", burn_note)
    T["publish"] = round(time.time() - t, 1)

    # ---- 8 gates ----
    t = time.time(); LOG("== verify")
    vi = probe(cfg, final_mp4)
    vd = RD.count_frames(cfg, final_mp4) / fps
    ad = read_wav(master)[0].shape[0] / 48000.0
    gates = [VF.gate_frames([tuple(x) for x in chunk_res], vd, ad, fps),
             VF.gate_words(cfg, words, removed_idx, ghost, fwords, edl),
             VF.gate_av(cfg, final_mp4, f16, src16, edl, video)]
    fdb, _ = TR.envelope_db(f16)
    _, fthr = TR.quiet_threshold(cfg, fdb)
    gates.append(VF.gate_captions(cfg, cues, chapters, f16, fthr)); gates[-1]["snap"] = snap
    gates.append(VF.gate_caption_coverage(cfg, cues, fwords))
    gates.append(VF.gate_loudness(cfg, RD.ebur128(cfg, final_mp4)))
    T["verify"] = round(time.time() - t, 1)
    ok = all(g["pass"] for g in gates)
    for g in gates:
        LOG(f"  gate {g['name']}: {'PASS' if g['pass'] else 'FAIL'}")
    if not ok:
        failed = os.path.join(out, f"{slug}.FAILED-GATES.mp4")
        os.replace(final_mp4, failed); final_mp4 = failed
        bp = os.path.join(out, f"{slug}.captioned.mp4")
        if os.path.exists(bp):
            os.replace(bp, os.path.join(out, f"{slug}.captioned.FAILED-GATES.mp4"))
    stats = {"raw_runtime": fmt_ts(duration), "final_runtime": fmt_ts(final_dur), "raw_s": round(duration, 2),
             "final_s": round(final_dur, 2), "pct_cut": f"{(1 - final_dur / duration) * 100:.0f}%",
             "retakes_cut": sum(1 for r in removals if r["action"] == "cut" and r["kind"] in ("cue", "restart")),
             "fillers_cut": sum(1 for r in removals if r["action"] == "cut" and r["kind"] in ("filler", "stutter")),
             "speedups": sum(1 for g in edl if g["speed"] != 1.0), "lufs_before": mres["before_raw"]["I"],
             "lufs_after": mres["final"]["I"], "gates_passed": ok, "stage_seconds": T}
    save_json(os.path.join(out, "stats.json"), stats)
    files = {"burn": burn_note, "mp4": final_mp4, "srt": srt, "sheet": sheet, "cuts_sheet": csheet, "thumbs": thumbs, "llm": bool(pkg)}
    write_review(ctx, mres, gates, files)
    if ok and not a.keep_work:
        for p in glob.glob(os.path.join(work, "chunks", "*.mp4")) + glob.glob(os.path.join(work, "screen_frames.u8")):
            os.remove(p)
    LOG(f"{'DONE' if ok else 'GATES FAILED'}: {final_mp4}  (review: {os.path.join(out, 'REVIEW.md')})")
    return 0 if ok else 2


def burn_captions(cfg, fwords, f16, work, final_mp4, slug, out):
    """Short 2-5 word chunks from the FINAL words, burned in with ffmpeg's subtitles filter (libass)."""
    r = common.run([common.ffbin(cfg, "ffmpeg"), "-hide_banner", "-filters"], check=False)
    if " subtitles " not in (r.stdout or ""):
        return "SKIPPED: this ffmpeg has no subtitles filter (build with libass, e.g. a full ffmpeg build); upload the .srt instead"
    c2 = json.loads(json.dumps(cfg))
    c2["publish"]["caption_max_words"] = cfg["publish"]["burn_max_words"]
    c2["publish"]["caption_max_chars"] = 32
    c2["publish"]["caption_min_sentence_words"] = 1
    cues = PB.build_cues(c2, fwords)
    PB.snap_cue_starts(c2, cues, f16, work)
    bs = os.path.join(work, "burn.srt")
    PB.write_srt(cues, bs)
    dst = os.path.join(out, f"{slug}.captioned.mp4")
    esc = bs.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    common.run([common.ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-i", final_mp4, "-vf",
                f"subtitles='{esc}':force_style='{cfg['publish']['burn_style']}'", "-c:v", "libx264", "-crf",
                str(cfg["render"]["x264_crf"]), "-preset", cfg["render"]["x264_preset"], "-pix_fmt", "yuv420p",
                "-c:a", "copy", "-map_chapters", "0", "-movflags", "+faststart", dst])
    return f"`{dst}` ({len(cues)} chunks of <= {cfg['publish']['burn_max_words']} words)"


def write_review(c, mres, gates, files, plan_only=False):
    cfg, edl, fps, duration, final_dur = c["cfg"], c["edl"], c["fps"], c["duration"], c["final_dur"]
    removals, decisions, out = c["removals"], c["decisions"], c["out"]
    ok = gates and all(g["pass"] for g in gates)
    status = "PLAN ONLY (not rendered)" if plan_only else ("ALL GATES PASSED" if ok else
                                                          "GATES FAILED: " + ", ".join(g["name"] for g in gates if not g["pass"]))
    L = [f"# REVIEW: {c['slug']}", "", f"**Status: {status}**", ""]
    sp_saved = sum((g["src_frames"] - g["frames"]) / fps for g in edl if g["speed"] != 1.0)
    by = {}
    for d in decisions:
        by[d.get("class", "?")] = by.get(d.get("class", "?"), 0) + d.get("removed_s", 0)
    proc = time.time() - c["t_start"]
    L += ["## Runtime", "", "| | |", "|---|---|",
          f"| Raw | {fmt_ts(duration)} ({duration:.1f}s) |", f"| Final | {fmt_ts(final_dur)} ({final_dur:.1f}s) |",
          f"| Removed | {duration - final_dur:.1f}s ({(1 - final_dur / duration) * 100:.1f}%) |",
          f"| retakes / stutters / fillers | {by.get('retake', 0):.1f}s |",
          f"| silent pauses tightened (static) | {by.get('static', 0):.1f}s |",
          f"| cursor-only pauses tightened | {by.get('cursor', 0):.1f}s |",
          f"| idle around on-screen action + speed-ups | {by.get('action', 0):.1f}s (speed-ups {sp_saved:.1f}s) |",
          f"| lead-in / run-out | {by.get('head', 0) + by.get('tail', 0):.1f}s |",
          f"| Processing time | {proc:.0f}s ({', '.join(f'{k} {v}s' for k, v in c['T'].items())}) |", ""]
    if gates:
        det = {"frames": lambda g: f"chunks off: {g['bad_chunks'] or 'none'}; video {g['video_s']}s vs audio {g['audio_s']}s ({g['diff_ms']} ms)",
               "words": lambda g: f"recall {g['recall'] * 100:.1f}% of {g['expected_words']} expected words; worst lost run {g['worst_run']} words",
               "av_sync": lambda g: f"max audio lag {g['max_audio_lag_ms']} ms over {len(g['points'])} probes",
               "captions": lambda g: f"cue start vs audio onset: median {g['overall_median']}s, p95 {g['overall_p95']}s (n={g['n']})",
               "caption_coverage": lambda g: f"{g['coverage'] * 100:.1f}% of final words inside a caption; uncovered: {g['uncovered'][:8] or 'none'}",
               "loudness": lambda g: f"I {g['I']} LUFS, LRA {g['LRA']} LU, true peak {g['TP']} dBTP"}
        L += ["## Gates", "", "| gate | result | detail |", "|---|---|---|"]
        L += [f"| {g['name']} | {'PASS' if g['pass'] else '**FAIL**'} | {det[g['name']](g)} |" for g in gates]
        L += [f"\n**WARNING ({g['name']}):** {g['warning']}" for g in gates if g.get("warning")] + [""]
    L += ["## Inputs", "", f"- Video: `{c['video']}`; output {fps:.3f} fps, same resolution as the source."]
    if c["sync"]:
        s = c["sync"]
        L.append(f"- Voice: `{s['mic']}` synced at {s['offset_s'] * 1000:+.1f} ms (confidence z={s['confidence_z']}).")
    L.append(f"- Footage kind: **{c['scr'].kind if c['scr'] else 'unknown'}** "
             "(screen = silent on-screen action is kept; camera = every silence is idle).")
    L.append("")
    cut = [r for r in removals if r["action"] == "cut"]
    flag = [r for r in removals if r["action"] != "cut"]
    main_cut = [r for r in cut if r["kind"] in ("cue", "restart")]
    small = [r for r in cut if r["kind"] not in ("cue", "restart")]
    L += [f"## Retakes removed ({len(main_cut)})", "", "Kept the LAST take each time.", "",
          "| id | src | out | kind | conf | removed | before ... | ... after (kept) |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['id']} | {r['s']:.2f} | {fmt_ts(r['out_t'])} | {r['kind']} | {r['confidence']} | {cell(r['removed_text'])} | "
          f"{cell(r['before'], 90)} | {cell(r['after'], 120)} |" for r in main_cut] or ["| - | | | | | none detected | | |"]
    L += ["", f"## Stutters and fillers removed ({len(small)})", ""]
    L += [f"- {r['id']} src {r['s']:.2f} ({r['kind']}, {r['confidence']}): \"{cell(r['removed_text'], 60)}\"" for r in small]
    L += ["", f"## Flagged, NOT cut ({len(flag)}): judge these against the transcript", ""]
    L += [f"- {r['id']} src {r['s']:.2f} (out {fmt_ts(r['out_t'])}) {r['kind']}: {r['why']}. Text: \"{cell(r['removed_text'], 120)}\"" for r in flag]
    L += [f"- {fmt_ts(d['out_t'])}: {d['flag']}" for d in decisions if d.get("flag")] + [""]
    rules = {"static": "silent + screen static: tightened to a natural gap (breath kept)",
             "cursor": f"silent + only the cursor moved: tightened to {cfg['deadspace']['cursor_only_gap_s']}s",
             "action": "silent but the screen is doing something: KEPT; idle trimmed; long ones sped up",
             "retake": "gap that contained a removed retake", "head": "before the first word", "tail": "after the last word"}
    cls = {}
    for d in decisions:
        cls.setdefault(d.get("class", "?"), []).append(d)
    L += ["## Dead-space decisions", "", f"Every silence >= {cfg['deadspace']['min_silence_s']}s. Full log: `decisions.csv`.", "",
          "| class | count | removed | rule |", "|---|---|---|---|"]
    L += [f"| {k} | {len(ds)} | {sum(d.get('removed_s', 0) for d in ds):.1f}s | {rules.get(k, '')} |" for k, ds in cls.items()]
    for d in cls.get("action", []):
        L.append(f"- action kept at src {d['src_s']:.2f} (out {fmt_ts(d['out_t'])}): {d['decision']}; {cell(d.get('why', ''), 140)}")
    L.append("")
    if mres:
        br, be, fi = mres["before_raw"], mres["before_edit"], mres["final"]
        L += ["## Loudness (EBU R128)", "", "| | integrated | LRA | true peak |", "|---|---|---|---|",
              f"| raw voice | {br['I']} LUFS | {br['LRA']} LU | {br['TP']} dBTP |",
              f"| edited, before mastering | {be['I']} LUFS | {be['LRA']} LU | {be['TP']} dBTP |",
              f"| final master | {fi['I']} LUFS | {fi['LRA']} LU | {fi['TP']} dBTP |", "",
              f"Chain: `{mres['chain']}`, then gain {mres['gain_db']:+.1f} dB + limiter. Voice only, no music bed.", ""]
    if gates:
        cap = next(g for g in gates if g["name"] == "captions")
        L += ["## Caption sync per chapter (SRT from the FINAL audio)", "",
              "| chapter | at | cues measured | median | p95 | result |", "|---|---|---|---|---|---|"]
        L += [f"| {cell(p['chapter'], 50)} | {fmt_ts(p['t'])} | {p['n']} | {p['median']} | {p['p95']} | {'PASS' if p['pass'] else 'FAIL'} |"
              for p in cap["per_chapter"]]
        av = next(g for g in gates if g["name"] == "av_sync")
        L += ["", "## A/V sync probes", "", "| out | src | audio lag | corr | frame diff here | best +-0.5s | picture |", "|---|---|---|---|---|---|---|"]
        L += [f"| {fmt_ts(p['out_t'])} | {p['src_t']} | {p.get('audio_lag_ms')} ms | {p.get('audio_z')} | {p.get('mad_here', '-')} | "
              f"{p.get('mad_pm05', '-')} | {'ok' if p.get('video_ok', True) else 'SHIFTED'} |" for p in av["points"]]
        wg = next(g for g in gates if g["name"] == "words")
        L += ["", "## Words check", "", f"Recall {wg['recall'] * 100:.1f}% ({wg['expected_words']} expected, {wg['final_words']} heard). "
              "Runs of 3+ expected words not heard:"]
        L += [f"- src {r['src_t']}: expected \"{cell(r['expected'], 120)}\" heard \"{cell(r['heard'], 80)}\"" for r in wg["missing_runs"][:25]] or ["- none"]
        L.append("")
    if files:
        L += ["## Files", "", f"- Video: `{files['mp4']}`", f"- Captions: `{files['srt']}`",
              f"- Chapters: `{os.path.join(out, 'chapters.txt')}` ({'titled by the claude CLI' if files['llm'] else 'heuristic titles: rewrite'})",
              f"- Burned-in captions: {files['burn'] or 'not requested (--burn-captions)'}",
              f"- Publish draft: `{os.path.join(out, 'PUBLISH.md')}`", f"- Contact sheet (LOOK AT IT): `{files['sheet']}`",
              f"- Edit-point sheet (LOOK AT IT): `{files['cuts_sheet']}`", f"- Stats: `{os.path.join(out, 'stats.json')}`"]
        L += [f"- Thumbnail candidate: `{t['path']}` (at {fmt_ts(t['t'])})" for t in files["thumbs"]] + [""]
    L += ["## Fixing a decision", "", f"Write `{os.path.join(out, 'overrides.json')}` and re-run the same command (cached):", "",
          "```json", '{"keep_retakes": ["R03"], "cut_retakes": ["R07"],',
          ' "keep_ranges": [[312.0, 330.5]], "force_cut": [{"s": 100.2, "e": 104.9, "why": "cough"}]}', "```",
          "Times are SOURCE seconds (the `src` column).", ""]
    with open(os.path.join(out, "REVIEW.md"), "w") as f:
        f.write("\n".join(L))
