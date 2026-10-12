"""Word-level transcription (whisper.cpp `whisper-cli`) + energy envelope helpers.

Words are {w, s, e, p}: text, start s, end s, confidence 0-1. Any other transcriber works if you hand the
pipeline a words.json in that shape (--words)."""
import os, re, json, math
import numpy as np
from .common import run, expand, read_wav, ffbin


def transcribe(cfg, wav16, out_prefix, prompt=None):
    js = out_prefix + ".json"
    if not os.path.exists(js):
        t = cfg["transcribe"]
        model = expand(cfg["paths"]["whisper_model"])
        if not os.path.exists(model):
            raise SystemExit(f"whisper model not found: {model}\nSet paths.whisper_model in your config "
                             "(e.g. ggml-small.en.bin from huggingface.co/ggerganov/whisper.cpp), or pass --words.")
        cmd = [ffbin(cfg, "whisper_bin"), "-m", model, "-f", wav16, "-ojf", "-of", out_prefix,
               "-ml", "1", "-sow", "-t", str(t["threads"]), "-bs", str(t["beam_size"]), "-np"]
        cmd += [str(a) for a in t.get("extra_args", [])]
        p = prompt if prompt is not None else t.get("prompt")
        if p:
            cmd += ["--prompt", p]
        run(cmd)
    d = json.load(open(js))
    if isinstance(d, list):          # a plain words.json from another transcriber
        return d
    words = []
    for seg in d["transcription"]:
        toks = [k for k in seg.get("tokens", []) if not k["text"].startswith("[_")]
        text = "".join(k["text"] for k in toks).strip()
        if not text or not re.search(r"[A-Za-z0-9]", text):
            if words and text:
                words[-1]["w"] += text          # punctuation-only segment joins the previous word
            continue
        ps = [max(1e-4, k["p"]) for k in toks if re.search(r"[A-Za-z0-9]", k["text"])]
        conf = math.exp(sum(math.log(x) for x in ps) / len(ps)) if ps else 0.0
        s, e = seg["offsets"]["from"] / 1000.0, seg["offsets"]["to"] / 1000.0
        words.append({"w": text, "s": s, "e": max(e, s + 0.02), "p": round(conf, 3)})
    for i in range(1, len(words)):
        if words[i]["s"] < words[i - 1]["s"]:
            words[i]["s"] = words[i - 1]["s"]
    return words


def envelope_db(wav16, hop_ms=10):
    a, sr = read_wav(wav16)
    a = a[:, 0]
    hop = int(sr * hop_ms / 1000)
    n = len(a) // hop
    fr = a[: n * hop].reshape(n, hop)
    rms = np.sqrt((fr.astype(np.float64) ** 2).mean(axis=1))
    return 20 * np.log10(rms + 1e-9), hop_ms / 1000.0


def quiet_threshold(cfg, db):
    ad = cfg["audio_detect"]
    floor = float(np.percentile(db, ad["floor_percentile"]))
    thr = min(floor + ad["quiet_above_floor_db"], ad["quiet_max_db"])
    return floor, thr


def quiet_runs(db, thr, hop, min_len):
    q = db < thr
    runs, s = [], None
    for i, v in enumerate(q):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if (i - s) * hop >= min_len:
                runs.append((s * hop, i * hop))
            s = None
    if s is not None and (len(q) - s) * hop >= min_len:
        runs.append((s * hop, len(q) * hop))
    return runs
