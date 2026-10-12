# The method, with every threshold

All values are in `config.example.json`; the file names below are in `scripts/lf/`.

## Pipeline

| stage | file | output (in `<outbox>/<slug>/`) |
|---|---|---|
| ingest: probe, extract 16 kHz + 48 kHz mono voice, sync a separate mic | `pipeline.py` | `work/src16.wav`, `work/src48.wav` |
| transcribe source (whisper.cpp, one word per segment `-ml 1 -sow`, JSON `-ojf`) | `transcribe.py` | `work/words_src.json` |
| screen activity (one decode at 8 fps, 480 px wide, grayscale memmap) | `screen.py` | `work/screen_*` |
| plan: retakes + silence decisions -> EDL on the frame grid | `retakes.py`, `plan.py` | `decisions.json`, `decisions.csv` |
| render: frame-exact chunks, audio overlap-add, master, mux | `render.py` | `work/video_edit.mp4`, `work/audio_master.wav` |
| re-transcribe FINAL audio, SRT, chapters, publish draft, sheets | `publish.py` | `<slug>.srt`, `chapters.txt`, `PUBLISH.md`, sheets, `thumbs/` |
| gates + review | `verify.py`, `pipeline.py` | `REVIEW.md`, `stats.json` |

## Silence measurement

- Envelope: RMS in 10 ms hops. Noise floor = 5th percentile. Quiet threshold = floor + 12 dB, capped at -40 dB.
- A gap between two words only counts as cuttable if a measured quiet run sits between their centres.
- Words whose energy never rises 3 dB above the quiet threshold are "ghosts" (whisper hallucinations): ignored.
- Breath pre-roll: up to 0.35 s of above-floor sound before a word is kept so the inhale is not clipped.

## Retake rules (`retakes.py`)

Phrases are split at pauses >= 0.45 s or sentence-ending punctuation.

| detector | rule | action |
|---|---|---|
| cue | cue phrase is (nearly) its own phrase, a later phrase re-says the opening of an earlier one within 45 s | cut from the abandoned attempt through the cue, keep the next take |
| cue, no match | isolated cue but no matching re-take | cut the sentence before the cue (medium confidence) |
| cue inside a sentence | "one more time" used normally | flag only |
| restart | first 2 content words equal, similarity >= 0.8 (0.9 if the earlier phrase was a complete sentence), <= 3 phrases between | cut the earlier attempt(s), keep the LAST |
| restart? | similarity 0.55-0.8 | flag only |
| stutter | same 1-5 word n-gram twice back to back | cut the first copy (single words need a gap >= 80 ms and are not on a whitelist like "that that") |
| self-correction | 3+ word run repeated within 3 words around "or / sorry / actually / wait / I mean" | cut the abandoned words |
| filler | um/uh/erm/hmm with >= 80 ms silence on one side | cut; glued fillers are flagged |

Any cut spanning > 30 s becomes a flag. Overrides (`keep_retakes`, `cut_retakes`) flip a decision by id.

## Dead-space rules (`plan.py`, `screen.py`)

| silence class | how it is detected | what happens |
|---|---|---|
| static | < 0.35 s of meaningful motion and net change < 0.3% | tightened to 0.28 s (mid-sentence) or 0.40 s (sentence end), min cut 0.25 s |
| cursor | only small compact blobs moved (blob < 0.4% of frame, aspect < 3) | tightened to 0.6 s |
| action | >= 0.35 s of motion above 0.15% of pixels, or net change >= 0.3% | span kept with 0.3 s pre-pad and 0.9 s result hold; idle either side trimmed |
| long action | action span > 4.5 s | sped up to land near 4 s, factor 1.5-3x in 0.5 steps, last 0.9 s at 1x; audio via atempo |
| head / tail | before the first word / after the last | keep 0.3 s lead-in / 1.0 s run-out |
| camera footage | most of the frame always moving, or file name matches `ingest.camera_name_regex` | every silence is static |

## Render details (`render.py`)

- Output fps: the source rate snapped to a standard rate. Chunks of <= 150 s of source, 2 in parallel.
- Video: `-copyts` seek, `fps` filter on the absolute grid, a `select` expression keeps exactly the kept frames
  (every k-th frame in sped segments), frame count checked per chunk. Concat with stream copy.
- Audio: each segment is placed at the output time of its first frame, 15 ms raised-cosine crossfades, read point
  nudged <= 3 ms to a zero crossing.
- Master chain (ffmpeg): `highpass=75`, `afftdn` (nr 10, floor from the measured noise), `equalizer` -2 dB at 220 Hz,
  +2 dB at 4 kHz, `highshelf` +1.5 dB at 10 kHz, `deesser`, `acompressor` -21 dB 2.5:1, gain to -14 LUFS, `alimiter`,
  up to 3 measure-and-correct passes until within 0.3 LU and the true peak is <= -1.5 dBTP. The chain's delay is
  measured by cross-correlation against the unprocessed edit and shifted back.
- Encoder: `libx264` CRF 17 by default; `"encoder": "videotoolbox"` for macOS hardware encoding (falls back to x264).

## Captions and chapters (`publish.py`)

- SRT cues: <= 8 words, <= 42 chars, <= 4.5 s, break on pauses > 0.6 s, sentence ends, commas after 5 words.
- Cue starts after a pause are moved to the voice-band (300-3000 Hz) onset within -0.30/+0.15 s (whisper word
  starts run ~80 ms late after silence).
- Burned captions (`--burn-captions`): <= 5 words per chunk, sentence ends always break, libass style from
  `publish.burn_style`.
- Chapter candidates: sentence starts scored +2 for structural openers ("the first", "next", "moving on", "step two"),
  +1.5 near a full-screen change, +1 after a long pause. Count = duration / 90 s, clamped 3-14, each >= 40 s apart.

## Gate details (`verify.py`)

- words: SequenceMatcher between kept source words and final words; near-identical replacements and whisper
  de-duplicating a repeated phrase count as present.
- av_sync: normalised cross-correlation of 2 s of source vs 2.4 s of final audio at each probe; the picture check
  compares the final frame with source frames at the mapped time and +-0.5 s (mean absolute difference, 320 px gray).
- captions: rising-energy onsets (>= 0.25 s quiet, then +6 dB) on the final audio; only cues that follow a pause are
  measurable; chapters with < 3 measurable cues pass by default and an overall p95 warning is raised instead.
