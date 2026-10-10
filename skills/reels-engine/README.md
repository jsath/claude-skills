# reels-engine

The reel editing skills live in their own repo, because they ship tools and
example code alongside the prompts:

**https://github.com/johannships/reels-engine**

It turns a raw talking-head take into an edited vertical reel: layouts that
switch per line, real screens and official logos, captions on every word,
voice plus synthesised sound effects, and hard QA gates before anything ships.

## Install the editing skill in Claude Code

```bash
git clone https://github.com/johannships/reels-engine.git
cp -r reels-engine/skills/edit-style ~/.claude/skills/
```

Then, in any folder with a raw take:

```
> use the edit-style skill to edit raw/take1.mov
```

## Other skills in that repo

| Skill | What it does |
|---|---|
| reel-ideation | Finds proven ideas: outliers against each creator's own median |
| signal-scout | Ranks audience signals from comments, transcripts and docs |
| content-strategist | Picks the few ideas worth making and says why |
| brief-builder | Turns one angle into a record-ready brief with a claim ledger |
| reel-scriptwriting | Writes the spoken script: hooks, curiosity, no AI slop |
| edit-style | Edits the raw take into the finished reel |
| house-reel-edit | The house editing style as one command driven by a beat sheet |
| reels-engine | Drives the full automated pipeline in that repo |

Copy any of them the same way (`cp -r reels-engine/skills/<name> ~/.claude/skills/`).

Editing needs Claude Code on a computer (ffmpeg, a local Whisper build and a
headless browser run on your machine). A Claude.ai chat cannot open or export
video files.
