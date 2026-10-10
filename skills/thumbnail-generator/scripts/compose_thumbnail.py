#!/usr/bin/env python3
"""Compose a 1280x720 YouTube thumbnail from a layout file, then check it.

usage: compose_thumbnail.py layout.json [--out thumb.png]
writes: thumb.png, thumb.preview.png (full size + the 320px and 168px sizes people actually see)
prints: overlap and out-of-frame checks; exit 1 if any FAIL

layout.json:
{
  "background": "plate.png",                      # any size, cover-fitted to 1280x720 (text-free image)
  "darken": 0.15,                                 # optional 0..1 overlay for contrast
  "cutout": {"path": "me_cutout.png", "side": "right", "height": 0.92, "outline": "white"},
  "texts": [
    {"text": "IT'S FREE", "block": "yellow", "x": 60, "y": 90, "size": 120, "rotate": -3},
    {"text": "NO SUBSCRIPTION", "block": "white", "x": 60, "y": 260, "size": 70}
  ],
  "logos": [{"path": "brand-logos/tool.png", "x": 60, "y": 520, "width": 220}],
  "font": "/path/to/Bold.ttf"                      # optional; Impact / Arial Bold / DejaVu Bold fallback
}
block colours: yellow (attention), green (positive), red (danger, white text), white (neutral), black.
"""
import argparse, json, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
BLOCKS = {"yellow": ("#FFD400", "black"), "green": ("#22C55E", "black"), "red": ("#E11D2E", "white"),
          "white": ("#FFFFFF", "black"), "black": ("#111111", "white")}
FONTS = ["/System/Library/Fonts/Supplemental/Impact.ttf", "/Library/Fonts/Impact.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "C:/Windows/Fonts/impact.ttf"]


def cover(img):
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def outline(cut, color, px=8):
    padded = Image.new("RGBA", (cut.width + 2 * px, cut.height + 2 * px), (0, 0, 0, 0))
    padded.alpha_composite(cut, (px, px)); cut = padded
    a = cut.split()[-1].filter(ImageFilter.MaxFilter(px * 2 + 1))
    ring = Image.new("RGBA", cut.size, color); ring.putalpha(a)
    ring.alpha_composite(cut)
    return ring


def shadow_paste(canvas, layer, x, y, off=6, blur=8):
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0)); sh.putalpha(layer.split()[-1].point(lambda v: v * 0.6))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(sh, (x + off, y + off)); canvas.alpha_composite(layer, (x, y))


def text_block(t, font_path, pad=8):
    font = ImageFont.truetype(font_path, t.get("size", 100))
    fill, ink = BLOCKS[t.get("block", "yellow")]
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), t["text"], font=font)
    w, h = box[2] - box[0] + 2 * pad, box[3] - box[1] + 2 * pad
    img = Image.new("RGBA", (w, h), fill)
    ImageDraw.Draw(img).text((pad - box[0], pad - box[1]), t["text"], font=font, fill=ink)
    if t.get("rotate"):
        img = img.rotate(t["rotate"], expand=True, resample=Image.BICUBIC)
    return img


def overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("layout"); ap.add_argument("--out", default="thumb.png")
    a = ap.parse_args()
    L = json.load(open(a.layout)); base = os.path.dirname(os.path.abspath(a.layout))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    font = L.get("font") or next((f for f in FONTS if os.path.exists(f)), None)
    if not font:
        sys.exit("no bold font found: set \"font\" in layout.json")
    canvas = cover(Image.open(P(L["background"])).convert("RGBA"))
    if L.get("darken"):
        canvas.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * L["darken"]))))
    boxes, fails = [], []
    face_box = None
    c = L.get("cutout")
    if c:
        cut = Image.open(P(c["path"])).convert("RGBA")
        cut = cut.crop(cut.getbbox())  # trim transparent padding before sizing
        if c.get("outline"):
            cut = outline(cut, c["outline"])
        th = int(H * c.get("height", 0.9)); s = th / cut.height
        if s > 1.15:
            print(f"WARN cutout upscaled {s:.2f}x: it will look soft. Use a bigger source.")
        cut = cut.resize((round(cut.width * s), th), Image.LANCZOS)
        x = W - cut.width - c.get("margin", 20) if c.get("side", "right") == "right" else c.get("margin", 20)
        y = H - cut.height  # flush with the bottom edge
        face_box = (x, y, x + cut.width, y + cut.height)
        if c.get("height", 0.9) < 0.7:
            fails.append("cutout under 70% of frame height: the face must dominate")
    for lg in L.get("logos", []):
        im = Image.open(P(lg["path"])).convert("RGBA"); im = im.crop(im.getbbox())
        s = lg["width"] / im.width; im = im.resize((lg["width"], round(im.height * s)), Image.LANCZOS)
        shadow_paste(canvas, im, lg["x"], lg["y"], off=4, blur=6)
        boxes.append(("logo " + os.path.basename(lg["path"]), (lg["x"], lg["y"], lg["x"] + im.width, lg["y"] + im.height)))
    for t in L.get("texts", []):
        im = text_block(t, font)
        shadow_paste(canvas, im, t["x"], t["y"])
        boxes.append((f"text '{t['text']}'", (t["x"], t["y"], t["x"] + im.width, t["y"] + im.height)))
    if c:
        canvas.alpha_composite(cut, (face_box[0], face_box[1]))  # face is the top layer
    words = sum(len(t["text"].split()) for t in L.get("texts", []))
    if words > 5:
        fails.append(f"{words} words of text: aim for 3, never more than 5")
    for name, b in boxes:
        if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H:
            fails.append(f"{name} leaves the frame {b}")
        if face_box and overlap(b, face_box):
            # bounding boxes are coarse: check the cutout's real pixels in that region
            region = cut.crop((max(0, b[0] - face_box[0]), max(0, b[1] - face_box[1]),
                               max(0, min(b[2], face_box[2]) - face_box[0]), max(0, min(b[3], face_box[3]) - face_box[1])))
            if region.width and region.height and region.split()[-1].getextrema()[1] > 0:
                fails.append(f"{name} overlaps the cutout")
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if overlap(boxes[i][1], boxes[j][1]):
                fails.append(f"{boxes[i][0]} overlaps {boxes[j][0]}")
    out = canvas.convert("RGB"); out.save(a.out)
    small = [out.resize((320, 180), Image.LANCZOS), out.resize((168, 94), Image.LANCZOS)]
    prev = Image.new("RGB", (W + 20 + 320, H), "#202020"); prev.paste(out, (0, 0))
    prev.paste(small[0], (W + 10, 10)); prev.paste(small[1], (W + 10, 210))
    pp = os.path.splitext(a.out)[0] + ".preview.png"; prev.save(pp)
    for f in fails:
        print("FAIL", f)
    print(f"{'PASS' if not fails else str(len(fails)) + ' FAIL(s)'} -> {a.out}, {pp} (now LOOK at the preview, small sizes first)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
