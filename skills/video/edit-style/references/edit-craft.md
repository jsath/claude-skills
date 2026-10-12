# Edit craft: shots, captions, screens, framing, audio, pitfalls

## 1. Shot plan

`shots.json`, one row per shot, anchored to words, never to hand-typed times:

```json
[
  {"layout": "FULL", "anchor": "Your AI agents", "content": "face"},
  {"layout": "PIP",  "anchor": "it's called", "content": "logo:brand-logos/acme.svg"},
  {"layout": "GFX",  "anchor": "2,000 stars", "content": "capture:shots/s3/"},
  {"layout": "GFX",  "anchor": "comment", "content": "card:CTA keyword"},
  {"layout": "FULL", "anchor": "see you", "content": "face"}
]
```

Resolve each `anchor` to the start time of its first word in `words.json`
(normalise case and punctuation). A shot ends where the next begins. Snap
boundaries to word starts so a cut never splits a name. If an anchor is not
found, stop and fix the plan: do not fall back to a guessed time.

**Adapting a reference reel?** Pull a contact sheet every ~0.5 s and use it
as the layout and timing reference (which layout when, how long each beat
holds, where text sits). Rebuild with your own take, live screenshots and
official logos. Never reuse its footage or graphics.

## 2. Compositing the layouts

FULL: `crop=<w:h:x:y from face_box.py --solve full>,scale=1080:1920`.

PIP (face card bottom, graphic top). Make the rounded mask once:

```bash
python3 -c "from PIL import Image,ImageDraw;m=Image.new('L',(1080,834),0);ImageDraw.Draw(m).rounded_rectangle([0,0,1079,833],radius=48,fill=255);m.save('mask.png')"
ffmpeg -i face.mp4 -i panel.mp4 -loop 1 -i mask.png -filter_complex \
 "[0:v]crop=<w:h:x:y from --solve pip>,scale=1080:834,setsar=1[f];[2:v]format=gray[m];[f][m]alphamerge[fc];\
  [1:v]scale=1080:1920,setsar=1[bg];[bg][fc]overlay=0:1086:shortest=1[v]" -map "[v]" ... shot.mp4
```

Heights must be even (yuv420p). Render every shot to its exact duration, concat
with the concat demuxer, then lay the ONE continuous tightened voice track over
the whole thing (never per-shot audio: seams click and drift).

Remotion pitfall: an `<OffthreadVideo>` inside `<Sequence from={X}>` restarts
at frame 0 unless it has `startFrom={X}`; every later shot then shows the
wrong moment while audio is right. Gate: compare face-box positions of the
final against the source at 0.1 s steps; the offset must be 0 in every shot.

## 3. Captions

| | graphic shots | talking-head shots |
|---|---|---|
| font | serif italic caps (Didot/Bodoni style) or the same bold sans | bold sans (Arial Bold, Inter Tight) |
| size | ~116 px, shrink to fit | ~64 px |
| vertical centre | 0.46 to 0.62 of height (0.38 on PIP) | ~0.72 |
| grouping | 1 to 2 words | 1 to 2 words |

- Caption TEXT from the script, TIMING from Whisper (`make_cues.py`). Using
  Whisper's text once put "THE CARPOTHE" on screen for "THE KARPATHY".
- Keep a fix map for names Whisper mangles (`{"cloud": "Claude"}`) and apply
  it to every pass, including the published SRT.
- Time cues from a re-transcription of the FINAL audio, never the raw take.
- Long words shrink to fit (`burn_captions.py` does it) instead of clipping.
- On PIP, captions sit at y 0.38 so a two-line cue never runs under the face
  card. Captions never cover the mouth.
- Burned captions run from the first word to the last. Bigger "punch phrase"
  type is extra, never a replacement.

## 4. Screens: clock-controlled headless capture

Screen-recording a monitor gives jitter, moire and a menu bar full of private
things. Instead `node tools/capture_clock.js <url> <outdir> [seconds] [warmup] [cssW] [cssH] [scale]`:

- headless only; the page clock (`performance.now`, `Date.now`,
  `requestAnimationFrame`) is frozen and stepped at 60 Hz, every 2nd frame kept
  for 30 fps, so slow machines cannot drop frames
- default 432x768 CSS at 2.5x = 1080x1920
- then `ffmpeg -framerate 30 -i <outdir>/f%04d.jpg -c:v libx264 -pix_fmt yuv420p clip.mp4`
- public pages, logged out. Recapture live numbers (stars, rankings) the day
  of render and note the capture time in QA.md
- highlight with outline boxes anchored to the real UI element, wiped in on
  the spoken word; pan and push in on the capture. No fake UI. A vendor's
  claim is shown as their own screenshot ("source: their README"), not restated.

## 5. Logos

- Official press/brand page or the site's own SVG first. For a GitHub repo,
  the org avatar (`https://github.com/<org>.png?size=460`) is the org's own
  mark. Favicon services are a low-res last resort, never for the hook.
- Never redraw, recolour, or AI-generate a logo. It names the subject; it does not imply endorsement.
- Cache each in `brand-logos/<brand>.svg|png` with a `SOURCES.md` line (source URL, date fetched).
- Render a labelled contact sheet of every logo and look at it before compositing.

## 6. Framing

Derive crops per take with `face_box.py --solve`. The solver:

```
H = (chin - head) / (chin_pct - head_pct)     y0 = head - head_pct * H
W = H * (out_w / out_h)                       x0 = centre_x - W/2
```

FULL targets head 13% / chin 85%; PIP 9% / 85%. Skin-tone face finders fail
silently against a warm wall; use a real detector. A one-frame head-top jump
is often a hand in front of the face: look at that frame first.

## 7. Gesture-anchored graphics (when the speaker points)

- Extract a frame at every reveal word and see where the finger really is. A
  right-handed speaker pointing overhead often sweeps right to left from the
  viewer's side: the mirror of reading order. Never assume left to right.
- Gate: re-extract a frame at each reveal and check the revealed element is
  on the side being pointed at.
- In blur-reveal formats every tile starts hidden and unblurs at its spoken
  word (word start minus ~0.12 s).

## 8. Editorial ("explainer") style

Text on a flat colour is a slide, not an edit. Real explainer short-form is:
real imagery with slow push-ins and text ON it; "receipt" cards (source
masthead + headline, or repo + live star count) as proof; one bold sans with
key words in a solid highlighter box; punch-ins on hard beats with 8 to 12
frame ease-outs. Count-ups must never show a wrong intermediate value when the
number is a claim: hard-cut claims, animate only decoration. Never cut to
moving footage of the speaker from another take (lips on different words).

## 9. Audio: voice + synthesised SFX, no music bed

```bash
ffmpeg -i tight.mp4 -vn -af "highpass=f=75,afftdn=nr=8" voice.wav
# SFX, generated so Content ID has nothing to match:
ffmpeg -f lavfi -i "sine=f=55:d=0.35" -af "afade=t=out:st=0.05:d=0.3" sub.wav            # sub hit on the hook word
ffmpeg -f lavfi -i "anoisesrc=d=0.35:c=pink:a=0.3" -af "highpass=f=800,afade=t=in:d=0.15,afade=t=out:st=0.15:d=0.2" whoosh.wav
```

Place SFX with `adelay` at shot boundaries, 12 to 20 dB under the voice peak
(if you notice them over the words, they are too loud). Few: a sub hit on the
hook, a soft whoosh on graphic cuts, clicks on highlights. "Royalty-free"
libraries are registered in Content ID; synthesise instead.

Master: measure integrated loudness `I` with `ebur128=peak=true`, apply
`volume=(-14 - I)dB,alimiter=limit=0.79:level=false`, re-measure the final
mp4, nudge the gain, repeat until -14 +/- 1 LUFS and true peak <= -1.5 dBTP.
Do not trust one-pass `loudnorm`: its linear mode silently falls back to dynamic.

## 10. Safe zones

On 1080x1920: top >= 220 px, bottom <= 1620 px, sides >= 60 px. Feeds crop to
4:5 (1080x1350, y 285 to 1635): every card, label and caption that carries
meaning must sit inside it. Captions at y ~1560 are safe; 1612 grazes the crop.

## 11. Recurring pitfalls

- Panels take data as props, never hard-coded content (panels have shipped
  showing a previous video's data). Forward props generically, or a new panel
  kind gets `undefined` and Remotion dies with "outputRange must contain only numbers".
- Sample frames proportionally, not at fixed timestamps: a shorter take runs past the end.
- Check `ffprobe` audio and video durations right after every render; an
  overloaded machine has silently dropped audio.
- Tables copied from internal notes drop any row with money or a client name.
- A spoken line that is factually false gets cut, not captioned, and is listed under CLAIMS.
