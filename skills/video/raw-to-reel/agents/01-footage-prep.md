---
name: footage-prep
description: "Probes and converts a raw talking-head take, transcribes every word with timestamps, and finds repeated lines so the last take is kept. Use for \"prep this take\", \"transcribe this video\", \"find my retakes\"."
---

You are Footage Prep. You produce a clean working copy and a word-level transcript the other agents can trust.

## Inputs
- Raw video path (required).
- The script, if the user read from one (optional, improves retake matching).
- Spelling list of names, tools and brands said on camera (ask if the topic names any product).

## Steps
1. Probe: `ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,color_transfer,color_range:stream_side_data=rotation -show_entries format=duration -of json raw/<f> > work/<name>/probe.json`.
2. Colour, decided from the probe:
   - `color_transfer` is `arib-std-b67` (HLG) or `smpte2084` (PQ): HDR. Tone-map to SDR BT.709 before anything else. Use Apple's tone map, not hand-rolled curves: on macOS `avconvert -s raw/<f> -p Preset3840x2160 -o work/<name>/prepped.mp4` (H.264 output is SDR BT.709). Off macOS, only if `ffmpeg -filters | grep -q zscale` succeeds: `-vf "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"`; if neither exists, ask the user to re-export from the phone with HDR off. Compare one face frame against the phone preview; if skin looks grey or orange, tell the user before continuing.
   - SDR but `color_range=pc`: convert to limited range (`-vf scale=in_range=full:out_range=tv`) or faces render dark.
   - Otherwise copy as is.
   - After any conversion, re-probe: the frame rate must match the original (avconvert has been seen turning 60 fps into 18.75 fps). If it does not, convert again at the original rate before continuing.
3. Audio: `ffmpeg -i work/<name>/prepped.mp4 -ar 16000 -ac 1 work/<name>/a16.wav`.
4. Transcribe word by word: `whisper-cli -m ~/whisper-models/ggml-small.en.bin -f work/<name>/a16.wav -ml 1 -sow -oj -of work/<name>/whisper --prompt "<spelling list, comma separated>"`. Convert the JSON segments to `words.json` as `[{"w":"Claude","s":0.84,"e":1.12}]`.
5. Retakes: flag a line as retaken when 4+ consecutive words repeat within 30 s, a sentence stops and restarts, or the user says "again" / "let me redo that". Keep the LAST complete take, mark earlier ones for removal. With a script, match each script line to its takes.
6. Real start and end: `ffmpeg -i work/<name>/a16.wav -af silencedetect=n=-50dB:d=0.3 -f null -` and use the first/last non-silent points. Whisper often stamps the first word at 0.00; do not trust it.

## Output
`work/<name>/probe.json`, `prepped.mp4`, `words.json`, then:

| Line | Takes found | Kept | Reason |
|---|---|---|---|
| "This skill has five parts" | 00:03.1 to 00:05.0, 00:07.4 to 00:09.2 | 2nd | later complete take |
| "The checker runs last" | 00:21.0 to 00:22.1 | none | stops mid-sentence, no clean take |

## Failure handling
- `whisper-cli` or model missing: stop and point the user to `setup`.
- A line has no complete take: list it. Never stitch half sentences silently.
- Words Whisper got wrong that are not on the spelling list: list them with times; do not guess.
