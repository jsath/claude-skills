# reels-engine

My full reel pipeline lives in its own repo, because it ships tools and
example code alongside the prompts:

**https://github.com/johannships/reels-engine**

It turns a raw talking-head take into an edited vertical reel: layouts that
switch per line, real screens and official logos, captions on every word,
voice plus synthesised sound effects, and hard QA gates before anything ships.

## The editing skill itself

The newest `edit-style` lives in this repo at [`../edit-style`](../edit-style),
with its tools and install check. Install it from here:

```bash
cp -r claude-skills/skills/edit-style ~/.claude/skills/
```

The reels-engine repo adds the rest of the pipeline around it (ideation,
scripting, Remotion graphic panels).

## Other skills in that repo

| Skill | What it does |
|---|---|
| reel-ideation | Finds proven ideas: outliers against each creator's own median |
| signal-scout | Ranks audience signals from comments, transcripts and docs |
| content-strategist | Picks the few ideas worth making and says why |
| brief-builder | Turns one angle into a record-ready brief with a claim ledger |
| reel-scriptwriting | Writes the spoken script: hooks, curiosity, no AI slop |
| house-reel-edit | The house editing style as one command driven by a beat sheet |
| reels-engine | Drives the full automated pipeline in that repo |

Copy any of them the same way (`cp -r reels-engine/skills/<name> ~/.claude/skills/`).

Editing needs Claude Code on a computer (ffmpeg, a local Whisper build and a
headless browser run on your machine). A Claude.ai chat cannot open or export
video files.
