"""Publish package: SRT (from the FINAL audio), chapters, title/description/pinned comment draft,
thumbnail candidates, contact sheet + cut-point sheet."""
import json, os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
from .common import run, ffbin, fmt_ts, LOG, save_json, norm

FONTS = ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]


def _font(size):
    for p in FONTS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ---------------- captions ----------------

def build_cues(cfg, words):
    P = cfg["publish"]
    cues, cur = [], []
    def flush():
        if cur:
            cues.append({"s": cur[0]["s"], "e": cur[-1]["e"], "text": " ".join(w["w"] for w in cur).strip()})
    for i, w in enumerate(words):
        if cur:
            text = " ".join(x["w"] for x in cur + [w])
            gap = w["s"] - cur[-1]["e"]
            sent = cur[-1]["w"].rstrip().endswith((".", "?", "!")) and len(cur) >= P.get("caption_min_sentence_words", 3)
            comma = cur[-1]["w"].rstrip().endswith(",") and len(cur) >= 5
            if (len(text) > P["caption_max_chars"] or len(cur) >= P["caption_max_words"] or gap > 0.6 or sent or comma
                    or w["e"] - cur[0]["s"] > P["caption_max_s"]):
                flush(); cur = []
        cur.append(w)
    flush()
    for i, c in enumerate(cues):
        nxt = cues[i + 1]["s"] if i + 1 < len(cues) else c["e"] + 1.0
        c["e"] = min(max(c["e"], c["s"] + 0.8), nxt - 0.04)
        c["e"] = max(c["e"], c["s"] + 0.2)
    return cues


def snap_cue_starts(cfg, cues, wav16, work):
    """Whisper -ml 1 word starts run ~0.08 s late after a pause. For cues that follow a pause, move the
    start to the voice-band (300-3000 Hz, 5 ms) onset found within [-0.30, +0.15] s. The caption gate
    measures with a different detector (broadband RMS, 10 ms) on the same final audio."""
    bp = os.path.join(work, "final16_voiceband.wav")
    run([ffbin(cfg, "ffmpeg"), "-v", "error", "-y", "-i", wav16, "-af", "highpass=f=300,lowpass=f=3000", bp])
    from .transcribe import envelope_db, quiet_threshold
    db, hop = envelope_db(bp, 5)
    # threshold from the room tone (20th percentile), not the absolute floor: a steady -46 dB room must
    # still count as "quiet before the cue"
    thr = min(float(np.percentile(db, 20)) + 8.0, -35.0)
    moved = []
    for i, c in enumerate(cues):
        i0, i1 = int((c["s"] - 0.45) / hop), int((c["s"] - 0.15) / hop)
        if i0 < 0 or np.mean(db[i0:i1] < thr) < 0.6:
            continue
        a, b = int((c["s"] - 0.30) / hop), int((c["s"] + 0.15) / hop)
        seg = db[a:b]
        up = np.where((seg[1:] >= thr) & (seg[:-1] < thr))[0]
        if len(up):
            t = (a + up[0] + 1) * hop
            prev_e = cues[i - 1]["e"] if i else 0.0
            if t > prev_e + 0.02:
                moved.append(t - c["s"]); c["s"] = round(t, 3)
            elif i and t > cues[i - 1]["s"] + 0.3:
                # the previous cue lingers into the pause; end it just before this onset
                cues[i - 1]["e"] = round(t - 0.02, 3)
                moved.append(t - c["s"]); c["s"] = round(t, 3)
    return {"snapped": len(moved), "median_shift_s": round(float(np.median(moved)), 3) if moved else 0.0}


def write_srt(cues, path):
    with open(path, "w") as f:
        for i, c in enumerate(cues, 1):
            f.write(f"{i}\n{fmt_ts(c['s'], ms=True)} --> {fmt_ts(c['e'], ms=True)}\n{c['text']}\n\n")


# ---------------- chapters ----------------

CUE_RE = re.compile(r"^(so\s+)?(the\s+)?(first|second|third|fourth|fifth|sixth|seventh|next|last|final|finally|number\s+\w+|"
                    r"moving on|let's talk about|let's get into|let's move|now let's|to wrap up|before we get into|"
                    r"the next one|repo number|step \w+)\b")


def chapter_candidates(cfg, words, hints):
    """Sentence starts scored by structural cues, long original pauses and big screen changes."""
    starts = []
    for i, w in enumerate(words):
        if i == 0 or words[i - 1]["w"].rstrip().endswith((".", "?", "!")):
            txt = " ".join(norm(x["w"]) for x in words[i:i + 6])
            sc = 0.0
            if CUE_RE.match(txt):
                sc += 2.0
            starts.append({"t": w["s"], "i": i, "score": sc, "lead": " ".join(x["w"] for x in words[i:i + 14])})
    st = np.array([s["t"] for s in starts]) if starts else np.zeros(0)
    for kind, times, wgt in (("screen", hints.get("screen", []), 1.5), ("pause", hints.get("pauses", []), 1.0)):
        for t in times:
            if len(st) == 0:
                break
            k = int(np.argmin(np.abs(st - t)))
            if abs(st[k] - t) <= 5.0:
                starts[k]["score"] += wgt
    return starts


def pick_chapters(cfg, cands, duration):
    P = cfg["publish"]
    n = int(max(3, min(P["chapter_max"], round(duration / P["chapter_target_s"]))))
    if duration < 3 * P["chapter_min_s"]:
        return [{"t": 0.0, "i": 0}]
    chosen = [{"t": 0.0, "i": 0, "lead": cands[0]["lead"] if cands else ""}]
    for c in sorted(cands, key=lambda c: -c["score"]):
        if len(chosen) >= n:
            break
        if c["score"] <= 0:
            break
        if c["t"] < P["chapter_min_s"] or duration - c["t"] < P["chapter_min_s"]:
            continue
        if all(abs(c["t"] - x["t"]) >= P["chapter_min_s"] for x in chosen):
            chosen.append(c)
    # fill long stretches evenly if cues were sparse
    chosen.sort(key=lambda c: c["t"])
    changed = True
    while changed and len(chosen) < n:
        changed = False
        bounds = [c["t"] for c in chosen] + [duration]
        gaps = [(bounds[i + 1] - bounds[i], i) for i in range(len(chosen))]
        g, i = max(gaps)
        if g < 2.2 * P["chapter_target_s"]:
            break
        mid = bounds[i] + g / 2
        best = min((c for c in cands if bounds[i] + P["chapter_min_s"] <= c["t"] <= bounds[i + 1] - P["chapter_min_s"]),
                   key=lambda c: abs(c["t"] - mid), default=None)
        if best:
            chosen.append(best); chosen.sort(key=lambda c: c["t"]); changed = True
    return chosen


def heuristic_title(lead):
    ws = re.sub(r"^(so|and|okay|alright|now|um|uh)[, ]+", "", lead.strip(), flags=re.I).split()
    t = " ".join(ws[:7]).rstrip(",.;:")
    return (t[:1].upper() + t[1:]) if t else "Chapter"


def chapter_text(words, chapters, duration):
    out = []
    bounds = [c["t"] for c in chapters] + [duration + 1]
    for i, c in enumerate(chapters):
        seg = [w["w"] for w in words if bounds[i] <= w["s"] < bounds[i + 1]]
        out.append(" ".join(seg))
    return out


def llm_package(cfg, words, chapters, cands, duration, work):
    """Ask the local Claude Code CLI for chapter titles + title/description/pinned comment. Optional."""
    P = cfg["publish"]
    if not P["use_claude_cli"]:
        return None
    import shutil
    if not shutil.which("claude"):
        return None
    texts = chapter_text(words, chapters, duration)
    full = " ".join(w["w"] for w in words)
    if len(full) > 60000:
        full = full[:60000] + " ..."
    cand_list = "\n".join(f"- {fmt_ts(c['t'])} ({c['t']:.1f}s): {c['lead']}" for c in cands if c["t"] >= P["chapter_min_s"])
    ch_list = "\n".join(f"- {fmt_ts(c['t'])} ({c['t']:.1f}s): {texts[i][:400]}" for i, c in enumerate(chapters))
    about = P.get("channel_context") or "a YouTube creator"
    prompt = f"""You are packaging a YouTube long-form video by {about}.
Below is the FINAL transcript (auto-transcribed, may misspell names).

Return ONLY a JSON object, no prose, with keys:
  "chapters": list of {{"t": seconds (number), "title": string}}. Start with t=0. Use ONLY start times from the
     SENTENCE STARTS list (you may drop or keep the proposed ones; 4-{P['chapter_max']} chapters, each >= {P['chapter_min_s']}s).
     Titles: <= 45 chars, concrete, what the viewer gets, no clickbait, no emoji, sentence case.
  "titles": 3 title options, <= 60 chars each, plain words, no clickbait words ("insane", "secret").
  "hook": 1-2 sentence description opener in the speaker's plain voice.
  "summary": 2-4 sentence description paragraph.
  "pinned_comment": 2-4 sentences: the one takeaway + a question to the viewer. Do not include links.
  "tags": up to 10 short tags.
  "flags": list of strings: any spoken claim with a number, price, star count or named company that must be
     fact-checked before publishing, quoted with its timestamp.
Rules: never invent numbers, prices or facts that are not in the transcript. Plain English. No "Not X. Y." antithesis.

PROPOSED CHAPTERS (with text):
{ch_list}

SENTENCE STARTS (allowed chapter times):
{cand_list}

FULL TRANSCRIPT:
{full}
"""
    try:
        r = subprocess.run(["claude", "-p", "--output-format", "json"], input=prompt, capture_output=True, text=True,
                           timeout=P["claude_timeout_s"], cwd=work)
        txt = r.stdout
        try:  # json envelope: keep the CLI-reported usage/cost for the edit log, then use the text result as before
            env = json.loads(txt)
            if isinstance(env, dict) and "result" in env:
                u = env.get("usage") or {}
                save_json(os.path.join(work, "llm_usage.json"), {
                    "source": "claude -p --output-format json (packaging call)", "usd": env.get("total_cost_usd"),
                    "tokens": sum((u.get(k) or 0) for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
                    "usage": u, "duration_ms": env.get("duration_ms")})
                txt = env.get("result") or ""
        except (ValueError, TypeError):
            pass
        m = re.search(r"\{.*\}", txt, re.S)
        if not m:
            return None
        d = json.loads(m.group(0))
        allowed = [c["t"] for c in cands] + [0.0]
        chs = []
        for c in d.get("chapters", []):
            t = float(c["t"])
            k = min(allowed, key=lambda a: abs(a - t))
            if abs(k - t) <= 2.0:
                chs.append({"t": k, "title": str(c["title"]).strip()[:60]})
        chs = sorted({c["t"]: c for c in chs}.values(), key=lambda c: c["t"])
        ok = []
        for c in chs:
            if not ok or c["t"] - ok[-1]["t"] >= P["chapter_min_s"] * 0.5:
                ok.append(c)
        if ok and ok[0]["t"] == 0.0 and len(ok) >= 3:
            d["chapters"] = ok
        else:
            d.pop("chapters", None)
        return d
    except Exception as e:
        LOG("  claude CLI packaging skipped:", str(e)[:200])
        return None


def youtube_chapters_ok(chs, duration):
    if not chs or chs[0]["t"] != 0 or len(chs) < 3:
        return False
    ts = [c["t"] for c in chs] + [duration]
    return all(ts[i + 1] - ts[i] >= 10 for i in range(len(chs)))


def write_ffmeta(chs, duration, path, title):
    with open(path, "w") as f:
        f.write(";FFMETADATA1\n")
        f.write(f"title={title}\n")
        for i, c in enumerate(chs):
            e = chs[i + 1]["t"] if i + 1 < len(chs) else duration
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(c['t']*1000)}\nEND={int(e*1000)}\ntitle={c['title']}\n")


# ---------------- frames ----------------

def grab(cfg, path, t, w=None):
    vf = ["-vf", f"scale={w}:-2"] if w else []
    r = subprocess.run([ffbin(cfg, "ffmpeg"), "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", path, "-frames:v", "1"] + vf +
                       ["-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if not r.stdout:
        return None
    arr = cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)) if arr is not None else None


def _label(im, text, size=18):
    d = ImageDraw.Draw(im)
    f = _font(size)
    tw = d.textlength(text, font=f)
    d.rectangle((4, 4, 12 + tw, 10 + size + 4), fill=(0, 0, 0))
    d.text((8, 6), text, font=f, fill=(255, 255, 255))
    return im


def apply_word_fixes(cfg, words):
    """publish.word_fixes {"cloud code": "Claude Code"}: whisper mishearings fixed in the FINAL words (captions, cue
    anchoring). Multi-word phrases are merged into one word spanning the originals. No fixes -> words unchanged."""
    fixes = cfg.get("publish", {}).get("word_fixes") or {}
    if not fixes or not words:
        return words
    import re as _re
    nk = lambda w: _re.sub(r"[^a-z0-9']", "", w.lower())
    pats = sorted(((k.lower().split(), v) for k, v in fixes.items() if not k.startswith("_")), key=lambda x: -len(x[0]))
    out, i = [], 0
    while i < len(words):
        hit = None
        for ks, v in pats:
            L = len(ks)
            if [nk(w["w"]) for w in words[i:i + L]] == [nk(k) for k in ks]:
                hit = (L, v); break
        if hit:
            L, v = hit
            tail = _re.search(r"[^\w']+$", words[i + L - 1]["w"])
            out.append({"w": v + (tail.group(0) if tail else ""), "s": words[i]["s"], "e": words[i + L - 1]["e"],
                        "p": min(w["p"] for w in words[i:i + L]), "fixed_from": " ".join(w["w"] for w in words[i:i + L])})
            i += L
        else:
            out.append(words[i]); i += 1
    return out


def contact_sheet(cfg, video, duration, out, cols=6, rows=5, w=384, title="", labeler=None):
    n = cols * rows
    tiles = []
    for i in range(n):
        t = (i + 0.5) * duration / n
        im = grab(cfg, video, t, w) or Image.new("RGB", (w, w * 9 // 16), (40, 0, 0))
        tiles.append(_label(im, fmt_ts(t) + (f"  {labeler(t)}" if labeler else "")))
    h = tiles[0].height
    head = 40
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 6, rows * h + (rows + 1) * 6 + head), (18, 18, 18))
    ImageDraw.Draw(sheet).text((10, 8), title, font=_font(22), fill=(230, 230, 230))
    for i, im in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet.paste(im.resize((w, h)), (6 + c * (w + 6), head + 6 + r * (h + 6)))
    sheet.save(out, quality=88)
    return out


def cuts_sheet(cfg, video, events, out, w=360, max_rows=14):
    """events: list of (out_t, label). Shows the frame 0.12 s before and after each edit point."""
    rows = []
    for t, lab in events[:max_rows]:
        a = grab(cfg, video, max(0, t - 0.12), w); b = grab(cfg, video, t + 0.05, w)
        if a is None or b is None:
            continue
        a = _label(a, f"{fmt_ts(t)} before", 16); b = _label(b, f"after  {lab}"[:44], 16)
        rows.append((a, b))
    if not rows:
        return None
    h = rows[0][0].height
    sheet = Image.new("RGB", (2 * w + 18, len(rows) * (h + 6) + 6), (18, 18, 18))
    for i, (a, b) in enumerate(rows):
        sheet.paste(a.resize((w, h)), (6, 6 + i * (h + 6))); sheet.paste(b.resize((w, h)), (12 + w, 6 + i * (h + 6)))
    sheet.save(out, quality=85)
    return out


def thumbnails(cfg, video, duration, edl, outdir, n=3):
    """Pick the sharpest, most colourful frame in each third of the video (1x-speed footage only)."""
    os.makedirs(outdir, exist_ok=True)
    picks = []
    for k in range(n):
        a, b = duration * k / n, duration * (k + 1) / n
        best = None
        for t in np.linspace(a + 2, b - 2, 12):
            if any(g["out_s"] <= t < g["out_e"] and g["speed"] != 1.0 for g in edl):
                continue
            im = grab(cfg, video, t, 480)
            if im is None:
                continue
            arr = np.asarray(im).astype(np.float32)
            g = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2GRAY)
            sharp = cv2.Laplacian(g, cv2.CV_64F).var()
            rg = arr[..., 0] - arr[..., 1]; yb = 0.5 * (arr[..., 0] + arr[..., 1]) - arr[..., 2]
            colour = np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
            sc = np.log1p(sharp) * (1 + colour / 40)
            if best is None or sc > best[0]:
                best = (sc, t)
        if best:
            p = os.path.join(outdir, f"thumb-{k+1}.png")
            full = grab(cfg, video, best[1])
            if full:
                full.save(p)
                picks.append({"path": p, "t": round(best[1], 2), "score": round(float(best[0]), 2)})
    return picks


# ---------------- PUBLISH.md ----------------

def cta_mentions(cfg, words, duration):
    keys = {norm(k) for k in cfg["publish"].get("cta_keywords", [])}
    hits = [round(w["s"], 1) for w in words if norm(w["w"]) in keys]
    return hits, [t for t in hits if 0.2 * duration <= t <= 0.8 * duration]


def write_publish(cfg, path, slug, chapters, pkg, words, duration, flags_extra):
    P = cfg["publish"]
    pkg = pkg or {}
    ch_txt = "\n".join(f"{fmt_ts(c['t'])} {c['title']}" for c in chapters)
    titles = pkg.get("titles") or [slug.replace("-", " ")]
    cta = P.get("cta_line") or ""
    lines = [f"# PUBLISH: {slug}", "", "Draft only. Nothing here has been uploaded or scheduled.", ""]
    lines += ["## Title options", ""] + [f"{i + 1}. `{t}` ({len(t)} chars)" for i, t in enumerate(titles)] + [""]
    lines += ["## Description", "", "```", pkg.get("hook", ""), "", pkg.get("summary", ""), ""]
    lines += ([cta, ""] if cta else []) + ["Chapters", ch_txt, "```", ""]
    lines += ["## Pinned comment", "", "```", pkg.get("pinned_comment", "") + (f"\n\n{cta}" if cta else ""), "```", ""]
    if pkg.get("tags"):
        lines += ["## Tags", "", "```", ", ".join(pkg["tags"]), "```", ""]
    lines += ["## Flags for the uploader", ""]
    if P.get("cta_keywords"):
        hits, mid = cta_mentions(cfg, words, duration)
        if mid:
            lines.append(f"- Mid-video call to action: found at {', '.join(fmt_ts(t) for t in mid[:4])}.")
        else:
            lines.append(f"- **MISSING:** no mid-video call to action (keywords {P['cta_keywords']}) between 20% and 80% "
                         f"of the runtime (mentions at: {', '.join(fmt_ts(t) for t in hits) or 'none'}).")
    lines.append(f"- End screen: add it in YouTube Studio over the last 20 s ({fmt_ts(max(0, duration - 20))} to {fmt_ts(duration)}).")
    for f in pkg.get("flags", []):
        lines.append(f"- FACT-CHECK: {f}")
    for f in flags_extra:
        lines.append(f"- {f}")
    if not pkg:
        lines.append("- Chapter titles, titles and description are heuristic drafts (claude CLI unavailable or --no-llm): rewrite before publishing.")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
