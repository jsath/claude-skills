"""Render the EDL: frame-exact video chunks (select filter) + sample-exact audio assembly + voice master.

Video: the EDL is split into chunks of <= chunk_source_s of source. Each chunk is one ffmpeg process that
seeks to the chunk, forces CFR on the absolute time grid, keeps exactly the frames of the kept segments
(sped-up segments keep every k-th frame) and encodes. Chunks are concatenated with stream copy. Every chunk's
frame count is checked against the EDL, so audio and video cannot drift.

Audio: numpy overlap-add. Each segment lands at the exact output time of its first video frame, with 15 ms
raised-cosine crossfades and the read point nudged <= 3 ms to a zero crossing. Sped-up segments are
time-stretched with atempo (no pitch change) and fit to their frame count.
"""
import os, math, json
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from .common import run, ffbin, read_wav, write_wav, LOG


def output_fps(cfg, info):
    f = cfg["render"]["fps"]
    if f != "auto":
        return float(f)
    v = info["video"]
    r = v["avg_fps"] if v["vfr"] and v["avg_fps"] else v["r_fps"]
    stds = [24000 / 1001, 24.0, 25.0, 30000 / 1001, 30.0, 50.0, 60000 / 1001, 60.0]
    best = min(stds, key=lambda s: abs(s - r))
    return best if abs(best - r) < 0.6 else (30.0 if r < 45 else 60.0)


def fps_str(fps):
    for n, d in ((30000, 1001), (60000, 1001), (24000, 1001)):
        if abs(fps - n / d) < 1e-6:
            return f"{n}/{d}"
    return str(int(fps)) if fps == int(fps) else f"{fps:.6f}"


def chunks_of(edl, max_src):
    out, cur = [], []
    for g in edl:
        if cur and g["e"] - cur[0]["s"] > max_src:
            out.append(cur); cur = []
        cur.append(g)
    if cur:
        out.append(cur)
    return out


def _select_expr(chunk, fps):
    h = 0.5 / fps
    terms = []
    for g in chunk:
        t = f"gte(t,{g['s'] - h:.6f})*lt(t,{g['e'] - h:.6f})"
        if g["speed"] != 1.0:
            t += f"*lt(mod(round((t-{g['s']:.6f})*{fps:.6f}),{g['speed']:g}),1)"
        terms.append(t)
    return "+".join(terms)


def _enc_args(cfg, w, h, fps, encoder=None):
    R = cfg["render"]
    enc = encoder or R["encoder"]
    g = str(int(round(fps * 2)))
    if enc == "videotoolbox":
        px = max(w, h)
        br = R["bitrate_2160"] if px > 2600 else R["bitrate_1440"] if px > 1920 else R["bitrate_1080"]
        m = float(br.rstrip("M"))
        return ["-c:v", "h264_videotoolbox", "-b:v", br, "-maxrate", f"{int(m * 1.6)}M", "-bufsize", f"{int(m * 2)}M",
                "-profile:v", "high", "-g", g, "-allow_sw", "1", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", R["x264_preset"], "-crf", str(R["x264_crf"]), "-g", g,
            "-pix_fmt", "yuv420p", "-profile:v", "high"]


def count_frames(cfg, p):
    r = run([ffbin(cfg, "ffprobe"), "-v", "error", "-select_streams", "v:0", "-count_packets",
             "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", p], check=False)
    try:
        return int(r.stdout.strip().split(",")[0])
    except Exception:
        return -1


def render_chunk(cfg, src, chunk, idx, work, fps, out_w, out_h, vf_extra=""):
    out = os.path.join(work, "chunks", f"c{idx:03d}.mp4")
    expect = sum(g["frames"] for g in chunk)
    if os.path.exists(out) and count_frames(cfg, out) == expect:
        return out, expect, expect
    X = max(0.0, math.floor(chunk[0]["s"] * fps) / fps)
    scale = f",scale={out_w}:{out_h}:flags=lanczos" if out_w else ""
    fl = (f"[0:v]setpts=PTS{scale}{vf_extra},fps=fps={cfg['_fps_str']}:start_time={X:.6f},"
          f"select='{_select_expr(chunk, fps)}',setpts=N/({fps:.6f}*TB),format=yuv420p[v]")
    base = [ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-copyts", "-ss", f"{X:.6f}", "-i", src,
            "-filter_complex", fl, "-map", "[v]", "-an", "-frames:v", str(expect)]
    tail = ["-r", cfg["_fps_str"], "-video_track_timescale", "90000", out]
    try:
        run(base + _enc_args(cfg, out_w, out_h, fps) + tail)
    except RuntimeError:
        if cfg["render"]["encoder"] == "x264":
            raise
        LOG(f"  chunk {idx}: hardware encoder failed, retrying with libx264")
        run(base + _enc_args(cfg, out_w, out_h, fps, "x264") + tail)
    return out, expect, count_frames(cfg, out)


def render_video(cfg, src, edl, work, fps, out_w=None, out_h=None, vf_extra=""):
    os.makedirs(os.path.join(work, "chunks"), exist_ok=True)
    chs = chunks_of(edl, cfg["render"]["chunk_source_s"])
    LOG(f"  video: {len(edl)} segments in {len(chs)} chunks @ {fps:.3f} fps, encoder={cfg['render']['encoder']}")
    results = [None] * len(chs)
    with ThreadPoolExecutor(max_workers=max(1, min(3, cfg["render"]["parallel"]))) as ex:
        futs = {ex.submit(render_chunk, cfg, src, c, i, work, fps, out_w, out_h, vf_extra): i for i, c in enumerate(chs)}
        for f in futs:
            i = futs[f]
            results[i] = f.result()
            LOG(f"  chunk {i + 1}/{len(chs)}: frames {results[i][2]}/{results[i][1]}")
    lst = os.path.join(work, "chunks", "list.txt")
    with open(lst, "w") as f:
        for p, _, _ in results:
            f.write(f"file '{p}'\n")
    vid = os.path.join(work, "video_edit.mp4")
    run([ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid])
    return vid, [r[1:] for r in results]


# ---------------- audio ----------------

def _zc_shift(x, n, rad):
    """Offset (samples, |d|<=rad) from n to the nearest zero crossing."""
    a, b = max(1, n - rad), min(len(x) - 1, n + rad)
    if b <= a:
        return 0
    seg = x[a - 1:b + 1]
    zc = np.where(np.signbit(seg[:-1]) != np.signbit(seg[1:]))[0]
    if len(zc) == 0:
        return 0
    cand = zc + a - 1 - n
    return int(cand[np.argmin(np.abs(cand))])


def assemble_audio(cfg, master48, edl, fps, work):
    x, sr = read_wav(master48)
    x = x[:, 0]
    total = int(round(edl[-1]["out_e"] * sr)) if edl else 0
    y = np.zeros(total + sr, np.float32)
    X = int(cfg["render"]["xfade_ms"] * sr / 1000)
    Z = int(cfg["render"]["zero_cross_ms"] * sr / 1000)
    fade = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, X))).astype(np.float32) if X > 1 else None
    tmp_in, tmp_out = os.path.join(work, "_seg_in.wav"), os.path.join(work, "_seg_out.wav")
    for i, g in enumerate(edl):
        o0 = int(round(g["out_s"] * sr)); o1 = int(round(g["out_e"] * sr))
        n = o1 - o0
        s0 = int(round(g["s"] * sr)); s1 = int(round(g["e"] * sr))
        first, last = i == 0, i == len(edl) - 1
        if g["speed"] == 1.0:
            d = _zc_shift(x, s0, Z) if not first else 0
            a = s0 + d - (0 if first else X // 2)
            b = s0 + d + n + (0 if last else X - X // 2)
            seg = np.zeros(b - a, np.float32)
            lo, hi = max(0, a), min(len(x), b)
            if hi > lo:
                seg[lo - a:hi - a] = x[lo:hi]
        else:
            src = x[max(0, s0 - X // 2): min(len(x), s1 + X)]
            write_wav(tmp_in, src, sr)
            k = g["speed"]
            run([ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-i", tmp_in, "-af", f"atempo={k:g}", "-c:a", "pcm_s32le", tmp_out])
            st, _ = read_wav(tmp_out)
            st = st[:, 0]
            want = n + (0 if first else X // 2) + (0 if last else X - X // 2)
            seg = np.zeros(want, np.float32); seg[:min(want, len(st))] = st[:want]
            a = s0 - (0 if first else X // 2)
        pos = o0 - (0 if first else X // 2)
        if fade is not None:
            if not first:
                seg[:X] *= fade
            if not last:
                seg[-X:] *= fade[::-1]
        p0 = max(0, pos)
        y[p0:pos + len(seg)] += seg[p0 - pos:]
    y = y[:total]
    out = os.path.join(work, "audio_edit.wav")
    write_wav(out, y, sr)
    for p in (tmp_in, tmp_out):
        if os.path.exists(p):
            os.remove(p)
    return out


# ---------------- mastering ----------------

def ebur128(cfg, path):
    r = run([ffbin(cfg, "ffmpeg"), "-nostats", "-hide_banner", "-i", path, "-vn", "-af",
             "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], check=True)
    txt = r.stderr
    i = txt.rfind("Summary:")
    s = txt[i:]
    def grab(key, unit):
        import re
        m = re.search(key + r":\s*(-?[\d.]+|-inf)\s*" + unit, s)
        return float(m.group(1)) if m and m.group(1) != "-inf" else float("-inf")
    return {"I": grab("I", "LUFS"), "LRA": grab("LRA", "LU"), "TP": grab("Peak", "dBFS")}


def master_audio(cfg, edit_wav, floor_db, work):
    M = cfg["master"]
    nf = max(-80, min(-25, floor_db))
    chain = [f"highpass=f={M['highpass_hz']}:poles=2"]
    if M["denoise"] == "afftdn":
        chain.append(f"afftdn=nr={M['denoise_nr_db']}:nf={nf:.0f}:tn=1")
    elif M["denoise"] == "arnndn" and M.get("arnndn_model"):
        chain.append(f"arnndn=m={M['arnndn_model']}:mix=0.8")
    chain += [f"equalizer=f={M['mud_cut_hz']}:t=q:w=1.0:g={M['mud_cut_db']}",
              f"equalizer=f={M['presence_hz']}:t=q:w=1.2:g={M['presence_db']}",
              f"highshelf=f=10000:g={M['air_db']}",
              f"deesser=i={M['deesser_intensity']}:m=0.5:f=0.5:s=o",
              f"acompressor=threshold={M['comp_threshold_db']}dB:ratio={M['comp_ratio']}:attack={M['comp_attack_ms']}:release={M['comp_release_ms']}:knee=2.5:makeup=1"]
    proc = os.path.join(work, "audio_proc.wav")
    run([ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-i", edit_wav, "-af", ",".join(chain), "-c:a", "pcm_f32le", proc])
    m1 = ebur128(cfg, proc)
    gain = M["target_lufs"] - m1["I"]
    lim = 10 ** (M["limiter_db"] / 20)
    final = os.path.join(work, "audio_master.wav")
    for attempt in range(3):
        run([ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-i", proc, "-af",
             f"volume={gain:.3f}dB,alimiter=limit={lim:.4f}:attack=3:release=60:level=false:asc=1,aresample=48000",
             "-ac", "2", "-c:a", "pcm_s24le", final])
        m2 = ebur128(cfg, final)
        if abs(m2["I"] - M["target_lufs"]) <= 0.3 and m2["TP"] <= M["target_tp_db"] + 0.3:
            break
        gain += M["target_lufs"] - m2["I"]
        if m2["TP"] > M["target_tp_db"] + 0.3:
            lim *= 10 ** ((M["target_tp_db"] - m2["TP"]) / 20)
    # filters with look-ahead / FFT windows (afftdn ~25 ms, alimiter ~3 ms) delay the signal: measure the
    # delay against the unprocessed edit and shift it back so lips stay in sync
    lat = _measure_delay(edit_wav, final)
    if abs(lat) > 0:
        y, sr = read_wav(final)
        n = int(round(lat * sr))
        y = np.concatenate([y[n:], np.zeros((n, y.shape[1]), np.float32)]) if n > 0 else np.concatenate([np.zeros((-n, y.shape[1]), np.float32), y[:n]])
        write_wav(final, y, sr)
        lat2 = _measure_delay(edit_wav, final)
        m2 = ebur128(cfg, final)
    else:
        lat2 = 0.0
    return final, {"chain": ",".join(chain), "gain_db": round(gain, 2), "after_chain": m1, "final": m2,
                   "latency_compensated_ms": round(lat * 1000, 2), "residual_latency_ms": round(lat2 * 1000, 2)}


def _measure_delay(ref_wav, test_wav, points=5):
    x, sr = read_wav(ref_wav); x = x.mean(axis=1)
    y, _ = read_wav(test_wav); y = y.mean(axis=1)
    dur = min(len(x), len(y)) / sr
    lags = []
    for T in np.linspace(5, max(6, dur - 6), points):
        a = x[int(T * sr): int((T + 1.0) * sr)]
        b = y[int((T - 0.1) * sr): int((T + 1.1) * sr)]
        if len(a) < sr or len(b) < len(a) or np.std(a) < 1e-4:
            continue
        c = np.correlate(b, a, "valid")
        lags.append(np.argmax(c) / sr - 0.1)
    return float(np.median(lags)) if lags else 0.0


def mux(cfg, video, audio, out, meta_file=None):
    R = cfg["render"]
    ac = R["audio_codec"]
    cmd = [ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-i", video, "-i", audio]
    if meta_file:
        cmd += ["-i", meta_file, "-map_metadata", "2", "-map_chapters", "2"]
    cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", ac, "-b:a", R["audio_bitrate"],
            "-ar", "48000", "-movflags", "+faststart", out]
    try:
        run(cmd)
    except RuntimeError:
        i = cmd.index(ac); cmd[i] = "aac"
        run(cmd)
    return out
