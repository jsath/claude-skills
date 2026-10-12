#!/usr/bin/env python3
"""Render an HTML file to PDF with headless Chromium (Playwright).

Usage:
    python render_pdf.py input.html output.pdf
    python render_pdf.py input.html output.pdf --png-dir qa/ --expect-pages 2

What it does:
    1. Opens the HTML in headless Chromium (never a visible window).
    2. Waits for the network to go idle and for web fonts to finish loading.
    3. Checks every fixed-size `.page` box for overflowing content.
    4. Prints to PDF using the CSS @page size (falls back to --format).
    5. Prints the page count, file size, and any warnings.
    6. With --png-dir, exports one PNG per PDF page for visual QA.

Exit code is 1 if --expect-pages does not match, or if a check fails and
--strict is set. Warnings are always printed.

Requires: pip install playwright pypdf && python -m playwright install chromium
Optional for PNGs: pip install pypdfium2 (or have `pdftoppm` from poppler).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Playwright is missing. Run: pip install playwright && python -m playwright install chromium")


OVERFLOW_JS = """
() => {
  const out = [];
  document.querySelectorAll('.page').forEach((p, i) => {
    const pr = p.getBoundingClientRect();
    if (p.scrollHeight > p.clientHeight + 1 || p.scrollWidth > p.clientWidth + 1) {
      out.push(`page ${i + 1}: content is larger than the page box`);
    }
    p.querySelectorAll('*').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (getComputedStyle(el).position === 'absolute') return;
      if (r.bottom > pr.bottom + 1 || r.right > pr.right + 1) {
        const tag = el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '');
        out.push(`page ${i + 1}: <${tag}> runs past the page edge`);
      }
    });
  });
  return [...new Set(out)].slice(0, 20);
}
"""

FONTS_JS = """
async () => {
  await document.fonts.ready;
  const bad = [];
  document.fonts.forEach(f => { if (f.status !== 'loaded') bad.push(`${f.family} ${f.weight} (${f.status})`); });
  return { count: document.fonts.size, bad: [...new Set(bad)] };
}
"""

IMAGES_JS = """
() => [...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src.slice(0, 80))
"""


def count_pages(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except ImportError:
        import re
        data = pdf_path.read_bytes()
        return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def export_pngs(pdf_path: Path, png_dir: Path, dpi: int) -> list:
    png_dir.mkdir(parents=True, exist_ok=True)
    for old in png_dir.glob("page-*.png"):
        old.unlink()
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(pdf_path))
        paths = []
        for i in range(len(doc)):
            img = doc[i].render(scale=dpi / 72).to_pil()
            out = png_dir / f"page-{i + 1:02d}.png"
            img.save(out)
            paths.append(out)
        return paths
    except ImportError:
        pass
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(png_dir / "page")], check=True)
        return sorted(png_dir.glob("page-*.png"))
    print("WARN  no PNG export: install pypdfium2 (pip install pypdfium2) or poppler (pdftoppm)")
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="HTML to PDF with headless Chromium, plus QA checks.")
    ap.add_argument("html", help="input HTML file")
    ap.add_argument("pdf", help="output PDF path")
    ap.add_argument("--png-dir", help="export one PNG per page here for visual QA")
    ap.add_argument("--dpi", type=int, default=110, help="PNG resolution (default 110)")
    ap.add_argument("--format", default="A4", help="fallback paper size if the HTML has no @page size (A4, Letter)")
    ap.add_argument("--expect-pages", type=int, help="fail if the PDF does not have exactly this many pages")
    ap.add_argument("--timeout", type=int, default=30000, help="page load timeout in ms")
    ap.add_argument("--strict", action="store_true", help="exit 1 on overflow, missing fonts or broken images")
    args = ap.parse_args()

    html = Path(args.html).resolve()
    pdf = Path(args.pdf).resolve()
    if not html.exists():
        sys.exit(f"Input not found: {html}")
    pdf.parent.mkdir(parents=True, exist_ok=True)

    warnings = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.emulate_media(media="print")
        try:
            page.goto(html.as_uri(), wait_until="networkidle", timeout=args.timeout)
        except Exception as e:  # slow fonts or remote images: render what we have, but say so
            warnings.append(f"load did not settle ({type(e).__name__}); rendering anyway")
            page.wait_for_timeout(2000)

        fonts = page.evaluate(FONTS_JS)
        if fonts["bad"]:
            warnings.append("fonts not loaded: " + ", ".join(fonts["bad"]))
        broken = page.evaluate(IMAGES_JS)
        if broken:
            warnings.append("images not loaded: " + ", ".join(broken))
        warnings += page.evaluate(OVERFLOW_JS)
        boxes = page.evaluate("() => document.querySelectorAll('.page').length")

        page.pdf(
            path=str(pdf),
            format=args.format,
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    pages = count_pages(pdf)
    size_kb = pdf.stat().st_size / 1024
    print(f"PDF   {pdf}")
    print(f"PAGES {pages}")
    print(f"SIZE  {size_kb:.0f} KB")
    if boxes:
        print(f"BOXES {boxes} .page elements in the HTML")
        if boxes != pages:
            warnings.append(f"{boxes} .page boxes but {pages} PDF pages: something spilled or a break is wrong")
    if size_kb > 10 * 1024:
        warnings.append("file is over 10 MB: compress images before sending")

    if args.png_dir:
        pngs = export_pngs(pdf, Path(args.png_dir).resolve(), args.dpi)
        for path in pngs:
            print(f"PNG   {path}")

    for w in warnings:
        print(f"WARN  {w}")

    if args.expect_pages is not None and pages != args.expect_pages:
        print(f"FAIL  expected {args.expect_pages} pages, got {pages}")
        return 1
    if args.strict and warnings:
        print("FAIL  warnings present and --strict is set")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
