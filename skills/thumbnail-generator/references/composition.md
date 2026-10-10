# Composition, text and layer order

## Canvas

- YouTube thumbnail: 1280x720. Design for 168x94 (sidebar and phone
  suggestions) and check at 320x180. The preview from `compose_thumbnail.py` shows both.
- The plate fills the whole canvas edge to edge. No dark voids or empty patches.

## Layouts that work

| layout | face | text | use |
|---|---|---|---|
| side split | one side, 85 to 95% of height, flush bottom | opposite side, upper half | default |
| centre face | centre, 90%+ | two blocks either side, upper third | reaction / shock |
| before/after | straddles the divider | one word per half | comparison, "replaces X" |

In split layouts, centre each element within its half; do not shove things to the edges.

## Sizes (at 1280x720)

| element | start at |
|---|---|
| cutout height | 85 to 95% of frame (never under 70%) |
| headline cap height | 110 to 140 px font size |
| secondary line | 60 to 80 px |
| logo | 180 to 260 px wide |
| outline around cutout | 6 to 10 px, white on dark plates, black on light |

If it looks big enough at full size, it is too small at 168 px.

## Text blocks

| block | text colour | meaning |
|---|---|---|
| yellow | black | attention, shock ("INSANE", "FREE") |
| green | black | positive, the solution ("EASY", "WORKS") |
| red | white | danger, warning ("EXPOSED", "DEAD") |
| white | black | neutral emphasis |

- Solid blocks, not stroked text floating on the image.
- Padding hugs the letters. Loose, boxy padding looks amateur.
- Drop shadow on every block. A slight rotation (-4 to 4 degrees) adds energy.
- Upper third or centre. Stack blocks vertically; do not let them touch.
- Watch letter collisions in mixed tokens ("in90"): keep a real space.

## Layer order (bottom to top)

plate, darken overlay, logos, text blocks, cutout. The face is always on top,
and nothing may cross it: if the script reports an overlap, move the text.

## What kills the click

- text-only thumbnails, or more than 5 words
- too many elements: if you have to look for the point, so does the viewer
- stock-photo energy, generic AI gradients
- small text that disappears on a phone
- a look identical to the channel's last three videos
