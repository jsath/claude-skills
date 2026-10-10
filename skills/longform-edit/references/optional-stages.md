# Optional stages (not in the scripts: how to add them)

The scripts cover the core edit. These stages sit on top of the clean final (`work/video_edit.mp4` +
`work/audio_master.wav`) and never change the cut or the audio. Each one is worth building only if you need it.
Whatever you add, keep the house rules: real content only, numbers only from `stats.json` or a cited source,
re-run the gates on the composited file, and look at frames yourself.

## 1. Graphics panels on cue words

A `graphics.json` in the inbox folder lists beats:

```json
{"beats": [
  {"id": "C01", "cue": "drop the file in a folder", "kind": "right", "hold_s": 3.0,
   "content": {"eyebrow": "Step 1", "text": "Drop the raw in the inbox"}},
  {"id": "C02", "cue": "and it cut", "kind": "lower", "hold_s": 2.5,
   "content": {"number": "{{pct_cut}}", "text": "of the raw removed"}}
]}
```

- Anchor each cue (3+ words) by fuzzy match (>= 0.8) in the FINAL re-transcription, in script order. An unheard cue
  is flagged in REVIEW with the closest words heard, never guessed.
- Kinds: `right`/`left` third-width panel, `lower` third, `title` band, `full` cutaway (a real image or clip).
- Numbers only through `{{placeholders}}` filled from `stats.json` (`raw_runtime`, `final_runtime`, `pct_cut`,
  `retakes_cut`, `lufs_after`...). An empty value means the beat is not placed and is flagged.
- Keep panels off the face: detect it (OpenCV YuNet face detector) over the beat's span and shrink or move the panel.
- Render panels with Remotion (or any HTML-to-video tool) as transparent ProRes 4444, overlay with ffmpeg, copy the
  audio stream untouched. Gate: same length, audio bit-identical, each panel visibly present in its window.

## 2. Scene switching (screen + camera recorded as separate tracks)

With a raw screen track and a raw webcam track you can compose three layouts: camera full-frame, screen with a round
camera bubble, and split (screen 2/3 + camera 1/3).

- Spec first: `"scenes": [{"cue": "let me show you", "scene": "screen"}]`, each holding until the next match.
- Otherwise auto: screen changing (the same activity measure as dead space) -> screen; static screen for > 4 s
  while talking -> camera; each auto scene >= 3 s.
- Snap every switch to a measured pause (or the deepest energy dip within 0.35 s), never mid-word.
- Gate: no black frame at a switch, the picture actually changes, and A/V probes stay >= 0.75 s from any switch.

## 3. Style profiles

A named bundle of overrides applied together, opt-in per video (`"style": "<name>"`). Example of what one can hold:

- Hook pacing: in the first ~2 min of output, pauses >= 0.40 s tighten to 0.24 s; gate fails if any remaining
  pause there is > 0.46 s (pauses kept for on-screen action are excused).
- Burned-in captions on every word in 2-5 word chunks, one emphasis word per chunk, placed clear of the face.
- Screen shown as a card with rounded corners and the camera as an inset; the OS menu bar cropped so clocks and
  notifications never ship.
- Synthesised sound effects (generated, never licensed audio) under switches and panel entrances, mixed before the
  final loudness pass so the voice still lands at -14 LUFS. Still no music bed.
- Slow 8% push-ins on long camera shots, anchored on the face.

## 4. External camera sync

When the screen recorder only captures a soft 720p webcam, record the camera onboard in 4K and sync it:

- GCC-PHAT on the camera's own audio vs the recorder's mic: a coarse 60 s window searched +-4 min, then ~8 windows
  of 30 s across the take searched +-1.5 s, and a line fit `cam_t = a + (1 + b) * t` where `b` is clock drift.
- Fewer than 2 confident windows means the file is from another take: fall back to the recorder's webcam and say so.
- Resample the drift when it adds up to >= 8 ms over the take; conform once to an intermediate at the output fps.
- Re-check the conformed file at the same windows (worst residual <= 20 ms). Start the camera first, then the
  recorder, then clap once in view.

## 5. Retake reveals

Replay a retake that was really cut, on purpose, as a 3-4 s insert: a short rewind of what was just seen, the raw
take with its original audio (desaturated, labelled with its source timecode), then a hard "cut" and back. Keep the
insert out of the SRT, the words gate and the A/V probes, and list the seconds it ADDS in REVIEW.
