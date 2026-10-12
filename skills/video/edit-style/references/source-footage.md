# Source footage: colour, cameras, clone takes, silence

## Identify the source first

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=color_range,color_transfer,r_frame_rate,width,height -of csv=p=0 raw.mov
```

| result | source | do |
|---|---|---|
| `tv,arib-std-b67` or Dolby Vision side data | iPhone HDR (HLG) | tone map with Apple's tool, below |
| `pc,bt709` | camera "SDR but full range" (e.g. some DJI Pocket modes) | decode as full range, output limited |
| `tv,bt709` | normal SDR | nothing special |

Also check the frame rate survived any conversion: a 60 fps take once came
out of a converter at 18.75 fps.

## iPhone HDR to SDR: use Apple's tone map, never hand-rolled maths

A numpy HLG curve once shipped a reel with an overexposed, orange face
(face median luma 148 to 167 vs Apple's 116, about 10% of pixels clipped).
On macOS extract frames with Apple's own HDR to SDR conversion:

```bash
# need.txt = space-separated frame indices at 60 fps, e.g. seq -s' ' 0 2399 > need.txt
sh tools/hdr_to_sdr_frames.sh raw.mov need.txt src 1350 2400 60
```

VFR-safe, writes `src/s%05d.jpg`, drop-in for an ffmpeg `fps=60` extract.
Then compare one face frame against `avconvert -p Preset1920x1080 -s raw.mov -o ref.mov`
and look. On Linux, use an ffmpeg build with `zscale` + `tonemap` or `libplacebo`.

## Full-range SDR cameras

Faces render about 12 levels too dark with crushed blacks if decoded as limited.
Use `zscale=rangein=full:range=limited` where available, otherwise
`-color_range pc` on the input plus
`scale=in_range=pc:out_range=tv:in_color_matrix=bt709:out_color_matrix=bt709`.
For frame extracts use `scale=in_range=pc:out_range=pc` so JPEGs keep real levels.

## Final encode (what `final_gates.sh` expects)

```
-vf "scale=in_range=pc:out_range=tv:in_color_matrix=bt601:out_color_matrix=bt709,format=yuv420p,setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
-color_range tv -color_primaries bt709 -color_trc bt709 -colorspace bt709
-c:v libx264 -profile:v high -preset slow -crf 17 -c:a aac -b:a 320k -ar 48000 -movflags +faststart
```

(The `in_*` values assume JPEG/PNG frames as input; for video input use that file's own range and matrix.)
Bitrate: never below 8 Mbps, aim for about 14. Flat graphics compress hard; if
the gate reports less, swap `-crf 17` for `-b:v 14M -maxrate 20M -bufsize 28M`.

## Skin-luma gate

```bash
sh tools/skin_luma_check.sh raw.mov 12.4 final.mp4 9.8 820:600:120:120 400:520:90:90
```

Boxes are `x:y:w:h` on a patch of cheek or forehead in each file's own pixels,
at the same spoken moment. A range mistake shows up as 10+ levels; pass is 2.

## Raw takes

- Keep the LAST take of any repeated line. Cut dead air and false starts. Never cut mid-word.
- Cut private third-party detail said in passing (someone's employer, a
  client, money). List each cut in QA.md so the owner can restore it.
- Trim leading dead air by audio energy, not Whisper (Whisper stamps the first
  word near 0.00 even when speech starts at 0.50). Cut to onset minus 0.1 s,
  then re-transcribe the first 2 s to prove the first word survived.

## Silence trimming: the setting that matters most

Edited reels have almost zero pauses (one reference reel had one 0.10 s pause
in 39.5 s; a raw take has around 26).

- **-50 dB threshold, never -38 dB.** On a typical voice a quarter of frames
  sit below -41 dB, so -38 dB treats consonants, word tails and breath as
  silence and cuts speech. That is exactly what "choppy" sounds like.
- `--min-pause` 0.16 to 0.22, `--keep` 0.10 to 0.13 (`tools/tighten.py`).
- **Never time-stretch the voice to fit the picture; re-time the picture.**
  Audio stretching is audible at +/-10%, video stretching is invisible at +/-25%.

## AI avatar (clone) takes, only as a fallback

A real raw take beats a clone on engagement. If you must use one:

- Pair avatar N with the voice recorded for avatar N; mismatched pairs sound wrong.
- Speaking speed 1.45 to 1.5 (slower reads as AI).
- One continuous render for the whole script: chunked renders drift.
- On many avatar platforms, voice "emotion" or stability settings are ignored
  for cloned voices; speed and pitch are the only real levers. Test before relying on them.
- Cutting silence is safe on clone takes: the avatar is near-motionless in pauses.
