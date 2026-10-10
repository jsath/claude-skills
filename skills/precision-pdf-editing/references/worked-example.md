# Worked example: one price column, two pages

A fictional case ("Acme Supplies" dealer price list) showing the full method.
Treat the numbers as an illustration, not a rule for other PDFs.

## The ask

"Add 150 to every value in the Dealer price column. Do not touch anything else."
The PDF is a two-page spreadsheet export with columns: row no., product, size,
Retail price, Promotion (empty), Dealer price.

## Finding the column

- Header text "Dealer price" plus geometry: Dealer values are right-aligned at a
  stable x, clearly separate from the Retail column and the empty Promotion column.
- `page.get_text("words")` put some values in a confusing order; the renders and
  the shared right edge settled it.

## Enumeration

```bash
python scripts/pdf_cells.py cells pricelist.pdf --x0 455 --x1 540 --add 150 --thousands comma > manifest.json
```

- Result: 111 cells, 68 on page 1 and 43 on page 2, matching the visible row count.
- The source printed row number 97 twice and skipped 98. Both rows were kept and
  told apart by product text and y-position. The source numbering was not fixed.

## Editing

- Values parsed as integers, plus 150, formatted with comma grouping like the source.
- The embedded Calibri subset contained every digit needed: no font fallback.
- Baseline and right edge preserved from measured glyph width.
- Redactions removed text only; images and line art were kept.
- One row on page 2 had a pale-yellow fill. The first attempt used a white
  redaction and produced a visible patch that passed every numeric check. Using
  the detected cell fill fixed it. This is why `fill` is in the manifest and why
  the visual review is not optional.

## Verification

- `diff` at 150 dpi, 3 px pad: zero changed pixels outside the masks on both pages.
- Every new value decodes once at its row, equal to source + 150.
- Non-target words identical by text plus bbox.
- `qpdf --check`, `pdftotext`, page size and rotation, metadata and trailer /ID all unchanged.
- Full-page and column-zoom renders inspected by eye.

## Lesson

A zero outside-mask diff proves unrelated regions are untouched. It does not
prove the edited cells look right. Always inspect the allowed regions for
background continuity, gridlines, clipping and leftover glyphs.
