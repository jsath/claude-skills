#!/usr/bin/env python3
"""Burn word captions onto a video without libass/drawtext (works on stripped ffmpeg builds).
Each cue is rendered to a transparent PNG with Pillow, then composited with ffmpeg overlay.

usage: burn_captions.py in.mp4 cues.json out.mp4 [--font PATH] [--size 64] [--y 0.72]
                        [--caps] [--color "#FFFFFF"] [--stroke 6] [--max-width 0.86] [--crf 17]
  cues.json  [{"text": "...", "start": s, "end": s}]   (from make_cues.py)
  --y        vertical CENTRE of the caption as a fraction of height (0.72 talking head, 0.38 over a PIP card)
Long words shrink to fit --max-width of the frame instead of clipping.
Output is tagged limited-range BT.709 yuv420p, the encode final_gates.sh expects.
"""
import argparse, json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]


def probe(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", f], capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


def render(text, font_path, size, W, maxw, color, stroke, path):
    s = size
    while True:
        font = ImageFont.truetype(font_path, s)
        box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font, stroke_width=stroke)
        if box[2] - box[0] <= W * maxw or s <= 20:
            break
        s -= 2
    w, h = box[2] - box[0] + 2 * stroke, box[3] - box[1] + 2 * stroke
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((stroke - box[0], stroke - box[1]), text, font=font, fill=color,
                             stroke_width=stroke, stroke_fill="black")
    img.save(path)
    return w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("cues"); ap.add_argument("out")
    ap.add_argument("--font"); ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--y", type=float, default=0.72); ap.add_argument("--caps", action="store_true")
    ap.add_argument("--color", default="#FFFFFF"); ap.add_argument("--stroke", type=int, default=6)
    ap.add_argument("--max-width", type=float, default=0.86); ap.add_argument("--crf", type=int, default=17)
    a = ap.parse_args()
    font = a.font or next((f for f in FONTS if os.path.exists(f)), None)
    if not font:
        sys.exit("no bold font found: pass --font /path/to/Font-Bold.ttf")
    W, H = probe(a.src)
    cues = json.load(open(a.cues))
    tmp = tempfile.mkdtemp(prefix="caps_")
    inputs, chain, last = ["-i", a.src], [], "0:v"
    for i, c in enumerate(cues):
        p = os.path.join(tmp, f"c{i:04d}.png")
        w, h = render(c["text"].upper() if a.caps else c["text"], font, a.size, W, a.max_width, a.color, a.stroke, p)
        inputs += ["-i", p]
        x, y = (W - w) // 2, int(H * a.y - h / 2)
        nxt = f"v{i}"
        chain.append(f"[{last}][{i + 1}:v]overlay={x}:{y}:enable='between(t,{c['start']:.3f},{c['end']:.3f})'[{nxt}]")
        last = nxt
    chain.append(f"[{last}]scale=out_range=tv:out_color_matrix=bt709,format=yuv420p,"
                 "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709[vout]")
    script = os.path.join(tmp, "graph.txt"); open(script, "w").write(";\n".join(chain))
    cmd = ["nice", "-n", "15", "ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex_script", script,
           "-map", "[vout]", "-map", "0:a?", "-c:a", "copy",
           "-color_range", "tv", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", str(a.crf), "-movflags", "+faststart", a.out]
    subprocess.run(cmd, check=True)
    print(f"burned {len(cues)} cues ({os.path.basename(font)}, {a.size}px, y={a.y}) -> {a.out}")


if __name__ == "__main__":
    main()
