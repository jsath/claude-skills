#!/usr/bin/env python3
"""Surgical, geometry-preserving value edits in an existing PDF, plus pixel QA.

Three subcommands (requires PyMuPDF: pip install pymupdf numpy):

  cells  SRC.pdf --x0 X --x1 X [--pages 1,2] [--pattern REGEX] [--add N] > manifest.json
         Enumerate every value whose glyphs sit inside the x-range, with
         character-level bbox, font, size, colour, baseline origin and the
         background fill under it. --add N fills "new" with old+N using the
         source grouping (e.g. 1,250 -> 1,400). Otherwise "new" is null and
         you fill it in yourself.

  apply  SRC.pdf OUT.pdf manifest.json
         Redact each glyph union with the cell's own fill colour (images and
         vector graphics kept), write the new text right-aligned on the same
         baseline, reusing the embedded font when it has every glyph needed.
         Restores the source metadata. Prints a JSON summary.

  diff   SRC.pdf OUT.pdf manifest.json [--dpi 150] [--pad 3]
         Render both at the same DPI and count changed pixels inside and
         outside the edit masks. Exit code 1 if anything changed outside.
"""
import argparse
import json
import re
import sys

try:
    import pymupdf as fitz
except ImportError:  # older installs
    try:
        import fitz
    except ImportError:
        sys.exit("PyMuPDF is required: pip install pymupdf numpy")

NUM_RE = r"^-?[0-9][0-9,.]*$"
BASE14 = {
    "Helvetica": "helv", "Helvetica-Bold": "hebo", "Helvetica-Oblique": "heit", "Helvetica-BoldOblique": "hebi",
    "Times-Roman": "tiro", "Times-Bold": "tibo", "Times-Italic": "tiit", "Times-BoldItalic": "tibi",
    "Courier": "cour", "Courier-Bold": "cobo", "Courier-Oblique": "coit", "Courier-BoldOblique": "cobi",
}


def parse_pages(spec, doc):
    if not spec:
        return list(range(len(doc)))
    return [int(p) - 1 for p in spec.split(",")]


def cell_fill(page, rect):
    """Return the RGB fill of the smallest filled drawing enclosing rect, else None (white)."""
    best = None
    for d in page.get_drawings():
        fill = d.get("fill")
        r = d.get("rect")
        if fill is None or r is None:
            continue
        if r.contains(rect):
            if best is None or r.get_area() < best[0].get_area():
                best = (r, fill)
    return list(best[1]) if best else None


def group_like(old, value, mode="auto"):
    """Format integer value with the same thousands separator style as old."""
    if mode == "comma":
        return f"{value:,}"
    if mode == "none":
        return str(value)
    if "," in old:
        return f"{value:,}"
    if "." in old and re.search(r"\.\d{3}(\D|$)", old):
        return f"{value:,}".replace(",", ".")
    return str(value)


def cmd_cells(a):
    doc = fitz.open(a.src)
    pat = re.compile(a.pattern)
    cells = []
    for pno in parse_pages(a.pages, doc):
        page = doc[pno]
        raw = page.get_text("rawdict")
        for block in raw["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    # split span chars into runs of non-space glyphs (alignment spaces excluded)
                    runs, cur = [], []
                    for ch in span["chars"]:
                        if ch["c"].isspace():
                            if cur:
                                runs.append(cur)
                            cur = []
                        else:
                            cur.append(ch)
                    if cur:
                        runs.append(cur)
                    for run in runs:
                        text = "".join(c["c"] for c in run)
                        x0 = min(c["bbox"][0] for c in run)
                        x1 = max(c["bbox"][2] for c in run)
                        if x0 < a.x0 or x1 > a.x1 or not pat.match(text):
                            continue
                        rect = fitz.Rect(x0, min(c["bbox"][1] for c in run), x1, max(c["bbox"][3] for c in run))
                        new = None
                        if a.add is not None:
                            digits = re.sub(r"[^0-9-]", "", text)
                            new = group_like(text, int(digits) + a.add, a.thousands)
                        cells.append({
                            "page": pno + 1,
                            "old": text,
                            "new": new,
                            "bbox": [round(v, 3) for v in rect],
                            "origin_y": round(run[0]["origin"][1], 3),
                            "right": round(x1, 3),
                            "font": span["font"],
                            "size": span["size"],
                            "color": span["color"],
                            "fill": cell_fill(page, rect),
                        })
    # uniqueness check: same page + bbox must not appear twice
    keys = [(c["page"], tuple(c["bbox"])) for c in cells]
    if len(keys) != len(set(keys)):
        sys.exit("duplicate cell geometry found; inspect the column manually")
    json.dump({"source": a.src, "x_range": [a.x0, a.x1], "count": len(cells), "cells": cells}, sys.stdout, indent=1, ensure_ascii=False)
    print(file=sys.stderr)
    print(f"{len(cells)} cells", file=sys.stderr)


def embedded_font(doc, page, fontname, cache):
    """Return (alias, fitz.Font) for an embedded font matching fontname, or (None, None)."""
    if fontname in cache:
        return cache[fontname]
    result = (None, None)
    for f in page.get_fonts(full=True):
        xref, basefont = f[0], f[3]
        if basefont.split("+")[-1] == fontname.split("+")[-1]:
            name, ext, _type, buf = doc.extract_font(xref)
            if buf:
                alias = f"R{xref}"
                page.insert_font(fontname=alias, fontbuffer=buf)
                result = (alias, fitz.Font(fontbuffer=buf))
            break
    if result[0] is None:
        # not embedded: a standard base-14 font can still be matched exactly
        base = fontname.split("+")[-1]
        if base in BASE14:
            result = (BASE14[base], fitz.Font(BASE14[base]))
    cache[fontname] = result
    return result


def cmd_apply(a):
    man = json.load(open(a.manifest))
    cells = man["cells"]
    missing = [c for c in cells if c.get("new") in (None, "")]
    if missing:
        sys.exit(f"{len(missing)} cells have no 'new' value; fill them before apply")
    doc = fitz.open(a.src)
    meta = dict(doc.metadata)
    by_page = {}
    for c in cells:
        by_page.setdefault(c["page"], []).append(c)
    fallbacks = []
    for pno, pcells in by_page.items():
        page = doc[pno - 1]
        cache = {}
        plans = []
        for c in pcells:
            alias, font = embedded_font(doc, page, c["font"], cache)
            if font is None or not all(font.has_glyph(ord(ch)) for ch in c["new"]):
                alias, font = "helv", fitz.Font("helv")
                fallbacks.append({"page": pno, "old": c["old"], "font": c["font"]})
            width = font.text_length(c["new"], fontsize=c["size"])
            new_x = c["right"] - width
            old = fitz.Rect(c["bbox"])
            union = old | fitz.Rect(new_x, old.y0, c["right"], old.y1)
            union = union + (-0.3, -0.3, 0.3, 0.3)
            fill = tuple(c["fill"]) if c["fill"] else (1, 1, 1)
            page.add_redact_annot(union, fill=fill)
            c["edit_rect"] = [round(v, 3) for v in union]
            plans.append((c, alias, new_x))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
        for c, alias, new_x in plans:
            rgb = fitz.sRGB_to_pdf(c["color"])
            page.insert_text((new_x, c["origin_y"]), c["new"], fontname=alias, fontsize=c["size"], color=rgb)
    doc.set_metadata(meta)
    doc.save(a.out, garbage=0, deflate=True, no_new_id=True)
    json.dump(man, open(a.manifest, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"out": a.out, "edited": len(cells), "font_fallbacks": fallbacks}, indent=1))
    if fallbacks:
        print("WARNING: fallback font used; output will not match source typography", file=sys.stderr)


def render(doc, pno, dpi):
    import numpy as np
    pix = doc[pno].get_pixmap(dpi=dpi, alpha=False)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)


def cmd_diff(a):
    import numpy as np
    man = json.load(open(a.manifest))
    src, out = fitz.open(a.src), fitz.open(a.out)
    if len(src) != len(out):
        sys.exit(f"page count differs: {len(src)} vs {len(out)}")
    scale = a.dpi / 72.0
    report, bad = [], False
    for pno in range(len(src)):
        if src[pno].rect != out[pno].rect or src[pno].rotation != out[pno].rotation:
            sys.exit(f"page {pno + 1} geometry/rotation differs")
        s, o = render(src, pno, a.dpi), render(out, pno, a.dpi)
        changed = np.any(s != o, axis=2)
        mask = np.zeros(changed.shape, dtype=bool)
        for c in man["cells"]:
            if c["page"] != pno + 1:
                continue
            r = c.get("edit_rect") or c["bbox"]
            x0 = max(int(r[0] * scale) - a.pad, 0)
            y0 = max(int(r[1] * scale) - a.pad, 0)
            x1 = int(r[2] * scale) + a.pad + 1
            y1 = int(r[3] * scale) + a.pad + 1
            mask[y0:y1, x0:x1] = True
        outside = int(np.count_nonzero(changed & ~mask))
        inside = int(np.count_nonzero(changed & mask))
        maxdiff = int(np.abs(s.astype(int) - o.astype(int))[~mask].max()) if (~mask).any() else 0
        report.append({"page": pno + 1, "changed_inside": inside, "changed_outside": outside, "max_outside_diff": maxdiff})
        bad = bad or outside > 0
    print(json.dumps({"dpi": a.dpi, "pad_px": a.pad, "pages": report, "pass": not bad}, indent=1))
    sys.exit(1 if bad else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cells")
    c.add_argument("src")
    c.add_argument("--x0", type=float, required=True)
    c.add_argument("--x1", type=float, required=True)
    c.add_argument("--pages")
    c.add_argument("--pattern", default=NUM_RE)
    c.add_argument("--add", type=int)
    c.add_argument("--thousands", choices=["auto", "comma", "none"], default="auto",
                   help="separator for --add results; auto copies each source cell, so 980+150 stays 1130")
    ap = sub.add_parser("apply")
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("manifest")
    d = sub.add_parser("diff")
    d.add_argument("src")
    d.add_argument("out")
    d.add_argument("manifest")
    d.add_argument("--dpi", type=int, default=150)
    d.add_argument("--pad", type=int, default=3)
    a = p.parse_args()
    {"cells": cmd_cells, "apply": cmd_apply, "diff": cmd_diff}[a.cmd](a)


if __name__ == "__main__":
    main()
