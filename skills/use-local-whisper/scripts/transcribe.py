#!/usr/bin/env python3
"""Local transcription with word timestamps. No API key, nothing leaves the machine.

usage:
  transcribe.py <audio_or_video> [--backend auto|whisper-cpp|faster-whisper|mlx]
                [--model PATH_OR_NAME] [--lang en] [--out DIR] [--words-per-cue 2]

writes into --out (default: next to the input):
  <stem>.words.json   [{"w": "Claude", "s": 1.20, "e": 1.48}, ...]   one entry per word, seconds
  <stem>.txt          plain transcript
  <stem>.srt          captions grouped --words-per-cue words per cue

backends (auto picks the first one installed, in this order):
  mlx            pip install mlx-whisper        Apple Silicon. default model mlx-community/whisper-large-v3-turbo
  faster-whisper pip install faster-whisper     any OS, CPU or CUDA. default model large-v3-turbo
  whisper-cpp    brew install whisper-cpp       needs --model path/to/ggml-*.bin (or WHISPER_MODEL env)
"""
import argparse, json, os, shutil, subprocess, sys, tempfile


def to_wav16k(src, tmpdir):
    wav = os.path.join(tmpdir, "audio16k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    return wav


def run_mlx(wav, model, lang):
    import mlx_whisper
    r = mlx_whisper.transcribe(wav, path_or_hf_repo=model or "mlx-community/whisper-large-v3-turbo",
                               word_timestamps=True, language=lang)
    return [{"w": w["word"].strip(), "s": w["start"], "e": w["end"]} for seg in r["segments"] for w in seg.get("words", [])]


def run_faster(wav, model, lang):
    from faster_whisper import WhisperModel
    m = WhisperModel(model or "large-v3-turbo", device="auto", compute_type="auto")
    segs, _ = m.transcribe(wav, word_timestamps=True, language=lang)
    return [{"w": w.word.strip(), "s": w.start, "e": w.end} for seg in segs for w in (seg.words or [])]


def run_cpp(wav, model, lang, tmpdir):
    model = model or os.environ.get("WHISPER_MODEL")
    if not model or not os.path.exists(model):
        sys.exit("whisper-cpp needs --model path/to/ggml-*.bin (see SKILL.md for the download line)")
    binary = os.environ.get("WHISPER_BIN") or shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    if not binary:
        sys.exit("whisper-cli not found: brew install whisper-cpp (or build whisper.cpp and set WHISPER_BIN)")
    base = os.path.join(tmpdir, "wc")
    # -ml 1 -sow = one segment per word, so segment times are word times
    r = subprocess.run([binary, "-m", model, "-f", wav, "-l", lang or "auto", "-ml", "1", "-sow", "-oj", "-of", base, "-np"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("whisper-cli failed:\n" + r.stderr[-2000:])
    data = json.load(open(base + ".json"))
    out = []
    for seg in data["transcription"]:
        t = seg["text"].strip()
        if t:
            out.append({"w": t, "s": seg["offsets"]["from"] / 1000, "e": seg["offsets"]["to"] / 1000})
    return out


def pick_backend():
    for name, mod in (("mlx", "mlx_whisper"), ("faster-whisper", "faster_whisper")):
        try:
            __import__(mod)
            return name
        except ImportError:
            pass
    if shutil.which("whisper-cli") or shutil.which("whisper-cpp") or os.environ.get("WHISPER_BIN"):
        return "whisper-cpp"
    sys.exit("no local Whisper found. Install one: pip install mlx-whisper | pip install faster-whisper | brew install whisper-cpp")


def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--model")
    ap.add_argument("--lang", default="en", help="language code, or 'auto'")
    ap.add_argument("--out")
    ap.add_argument("--words-per-cue", type=int, default=2)
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found: brew install ffmpeg (or your package manager)")
    lang = None if a.lang == "auto" else a.lang
    backend = pick_backend() if a.backend == "auto" else a.backend
    out = a.out or os.path.dirname(os.path.abspath(a.src))
    os.makedirs(out, exist_ok=True)
    stem = os.path.join(out, os.path.splitext(os.path.basename(a.src))[0])
    with tempfile.TemporaryDirectory() as tmp:
        wav = to_wav16k(a.src, tmp)
        if backend == "mlx":
            words = run_mlx(wav, a.model, lang)
        elif backend == "faster-whisper":
            words = run_faster(wav, a.model, lang)
        elif backend == "whisper-cpp":
            words = run_cpp(wav, a.model, a.lang, tmp)
        else:
            sys.exit(f"unknown backend {backend}")
    words = [{"w": w["w"], "s": round(w["s"], 3), "e": round(w["e"], 3)} for w in words if w["w"]]
    with open(stem + ".words.json", "w") as f:
        f.write("[\n" + ",\n".join(json.dumps(w, ensure_ascii=False) for w in words) + "\n]\n")
    open(stem + ".txt", "w").write(" ".join(w["w"] for w in words) + "\n")
    n = max(1, a.words_per_cue)
    with open(stem + ".srt", "w") as f:
        for i in range(0, len(words), n):
            g = words[i:i + n]
            f.write(f"{i // n + 1}\n{ts(g[0]['s'])} --> {ts(g[-1]['e'])}\n{' '.join(w['w'] for w in g)}\n\n")
    print(f"{backend}: {len(words)} words, {words[-1]['e'] if words else 0:.2f}s -> {stem}.words.json / .txt / .srt")


if __name__ == "__main__":
    main()
