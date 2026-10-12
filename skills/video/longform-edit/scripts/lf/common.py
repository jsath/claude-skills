"""Shared helpers: config, logging, subprocess, probing, wav IO."""
import json, os, re, subprocess, time, wave, shutil
import numpy as np

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def expand(p):
    return os.path.abspath(os.path.expanduser(p)) if isinstance(p, str) else p


def deep_merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(extra_paths=()):
    """config.example.json is the full default set; later files are deep-merged over it."""
    with open(os.path.join(SKILL_DIR, "config.example.json")) as f:
        cfg = json.load(f)
    for p in extra_paths:
        if p and os.path.exists(expand(p)):
            with open(expand(p)) as f:
                cfg = deep_merge(cfg, json.load(f))
    return cfg


class Log:
    def __init__(self):
        self.path = None
        self.t0 = time.time()

    def __call__(self, *msg):
        line = f"[{time.time()-self.t0:7.1f}s] " + " ".join(str(m) for m in msg)
        print(line, flush=True)
        if self.path:
            with open(self.path, "a") as f:
                f.write(line + "\n")


LOG = Log()


def run(cmd, check=True):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))[:400]}\n{(r.stderr or '')[-2500:]}")
    return r


def ffbin(cfg, name):
    p = cfg["paths"].get(name) or name
    return p if os.path.exists(expand(p)) else (shutil.which(p) or shutil.which(name) or name)


def probe(cfg, path):
    r = run([ffbin(cfg, "ffprobe"), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    d = json.loads(r.stdout)
    info = {"path": path, "duration": float(d["format"].get("duration", 0) or 0), "video": None, "audio": None}
    for s in d["streams"]:
        if s["codec_type"] == "video" and info["video"] is None and s.get("codec_name") not in ("mjpeg", "png"):
            n, dn = (s.get("r_frame_rate") or "0/1").split("/")
            an, ad = (s.get("avg_frame_rate") or "0/1").split("/")
            rfr = float(n) / float(dn) if float(dn) else 0
            afr = float(an) / float(ad) if float(ad) else 0
            info["video"] = {"codec": s.get("codec_name"), "width": int(s["width"]), "height": int(s["height"]),
                             "r_fps": rfr, "avg_fps": afr, "vfr": abs(rfr - afr) > 0.5 if afr else False}
        elif s["codec_type"] == "audio" and info["audio"] is None:
            info["audio"] = {"codec": s.get("codec_name"), "rate": int(s.get("sample_rate") or 0),
                             "channels": int(s.get("channels") or 0)}
    return info


def read_wav(path):
    with wave.open(path, "rb") as w:
        n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        a = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        i = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        i = np.where(i & 0x800000, i - 0x1000000, i)
        a = i.astype(np.float32) / 8388608.0
    else:
        raise ValueError("unsupported wav sample width")
    return a.reshape(-1, ch), sr


def write_wav(path, a, sr):
    a = np.asarray(a, dtype=np.float32)
    if a.ndim == 1:
        a = a[:, None]
    pcm = (np.clip(a, -1, 1) * 2147483647.0).astype(np.int32)
    with wave.open(path, "wb") as w:
        w.setnchannels(a.shape[1]); w.setsampwidth(4); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def extract_audio(cfg, src, dst, sr, offset=0.0, duration=None):
    """Mono wav of `src` so that dst[0] == src time `offset` (negative offset pads with silence)."""
    cmd = [ffbin(cfg, "ffmpeg"), "-v", "error", "-y"]
    af = []
    if offset > 0:
        cmd += ["-ss", f"{offset:.6f}"]
    cmd += ["-i", src, "-vn", "-map", "0:a:0"]
    if offset < 0:
        af.append(f"adelay={int(round(-offset * 1000))}:all=1")
    if duration:
        af.append(f"apad,atrim=0:{duration:.6f}")
    if af:
        cmd += ["-af", ",".join(af)]
    cmd += ["-ar", str(sr), "-ac", "1", "-c:a", "pcm_s32le" if sr >= 44100 else "pcm_s16le", dst]
    run(cmd)
    return dst


def fmt_ts(t, ms=False):
    t = max(0.0, t)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if ms:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"
    return f"{int(h)}:{int(m):02d}:{int(s):02d}" if h >= 1 else f"{int(m):02d}:{int(s):02d}"


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: float(o) if isinstance(o, np.floating)
                  else int(o) if isinstance(o, np.integer) else str(o))
    os.replace(tmp, path)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def norm(w):
    w = w.lower().replace("’", "'")
    return re.sub(r"[^a-z0-9']", "", w).strip("'")
