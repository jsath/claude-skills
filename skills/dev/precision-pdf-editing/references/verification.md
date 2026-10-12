# Verification checklist

Run every check. Report each as PASS, FAIL or NOT RUN with the command used.

## Structural and arithmetic

- Source and output page counts match.
- Page rectangles and rotations match exactly.
- Every target cell maps once and only once (manifest count equals visible rows).
- Every new value decodes once, at the expected position (`pdftotext -layout`, or
  `page.search_for(new_value)` and check the y-position).
- The transform holds for every row (recompute old to new from the manifest).
- Visible words outside the edit rectangles are identical by text plus bbox.
  Ignore block and line ids: overlay text streams legitimately renumber them.
- Metadata dictionary and trailer `/ID` match when preservation was required
  (`pdfinfo`, `doc.metadata`, `doc.pdf_trailer()`). Object counts and xref layout
  may change; that is expected.
- `qpdf --check` passes on the output.

## Pixel level

- Render source and output with the same renderer at the same DPI.
- Build masks from the PDF edit rectangles scaled to raster coordinates, padded by
  2 to 3 pixels for antialiasing.
- Count changed pixels inside and outside the masks separately.
- Strict target: zero changed pixels outside the masks, maximum outside channel
  difference zero.
- Open the difference images. Statistics cannot show a wrong background colour
  inside an allowed rectangle.

## Manual visual review

Look at full pages and high-zoom crops of every edited region:

- no clipping, overlap, leftover old glyphs, malformed separators, baseline drift;
- font, size, weight, colour and alignment match neighbouring cells;
- headers, gridlines, logos, images, row order and highlights intact;
- every intended edit visible, nothing unrelated changed.

## If a check fails

| Failure | Likely cause | Fix |
|---|---|---|
| Changed pixels outside masks | redaction removed line art, or edit rect too narrow for a wider new value | confirm `graphics` keep option; widen union to cover the new text |
| White patch on a coloured row | fill not detected (fill is an image or a pattern) | sample the render next to the glyphs and set `fill` manually in the manifest |
| New value in wrong font | subset font missing glyphs | report the fallback; ask for the full font file |
| Value decodes twice | old glyphs not fully covered | rebuild the manifest from character boxes, rerun apply on the original source |

Always rerun `apply` from the untouched source, never on a previous output.
