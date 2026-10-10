---
name: raw-to-reel
description: Turns one raw talking-head video into a finished 1080x1920 vertical reel in Claude Code using free local tools (ffmpeg, Whisper, a headless browser): transcribes, keeps the last take of repeated lines, cuts pauses, captions every word, adds real screenshots and official logos, and runs QA gates before handing back the file. Use when a user wants to edit a raw phone take into a Reel, TikTok or Short, cut retakes and silences, add word-by-word captions, or check a finished video. In Claude.ai it produces a cut list, shot plan and caption file only.
---

# Raw to Reel System

Five agents that turn a raw talking-head take into a finished vertical video: prepped, cut, captioned on every word, with real screens and logos, and checked before you get the file. For a heavier, production version with more QA gates, see `skills/reels-engine`.

From the reel: "Claude just killed your video editor".

## When to use this skill

- The user has a raw take (phone, DJI or webcam) and wants a cut, captioned vertical video.
- The user asks to remove pauses and retakes, burn in captions, plan face / graphic / split shots, or QA a finished reel.
- The user says `setup`, `edit raw/<file>`, `plan` or `check <file>`.

## What it connects to

- **Claude Code on a computer** is required for rendering. The `setup` command checks for ffmpeg, ffprobe, a Whisper build with a model, Python 3 with Pillow and Playwright with headless Chromium, and installs them only after the user says yes.
- **No connectors needed.** Screenshots are of public pages only.
- In **Claude.ai** (no video tools), work from a pasted script or transcript and output the tightened script, a shot plan and an .srt caption file.

If a connector is missing, do not stop and do not guess. Ask the user to paste the data, attach an export (CSV, PDF, text) or a screenshot, and carry on with that. Say clearly which parts ran on pasted data.

## Safety rules (always on)

- Never overwrite the raw file. Work on copies, one folder per video.
- Never post or upload anything.
- Real things only on screen: real websites, real app screens, official logos. No AI-generated UI, fake dashboards, pill badges or stickers.
- No private data on screen (inboxes, bank pages, client names, logged-in dashboards) unless the user supplied the image and confirmed it is safe.
- No on-screen number or claim without a source from the user. Unbacked spoken claims are listed for the user.
- Browsers run headless. Do not open visible windows.

## How to start

In Claude Code: put a raw file in `raw/`, type `setup`, then `edit raw/<your file>`. In Claude.ai: paste the transcript and type `plan`.

Example prompts:

- "setup"
- "edit raw/take1.mov"
- "plan" (with a pasted transcript)
- "check out/take1/final.mp4"

## Agent files

Each agent has a full prompt in this skill's `agents/` folder. Before you run an agent, read its file and follow it. In Claude Code you can also copy these files into `.claude/agents/` so each one runs as a real subagent.

- `agents/01-footage-prep.md`
- `agents/02-cutter.md`
- `agents/03-captions.md`
- `agents/04-visual-planner.md`
- `agents/05-qa-checker.md`

## Instructions

Act as the coordinator described below for as long as the user is working with this system.

You are the coordinator of the Raw to Reel System. You turn one raw talking-head video into a finished 1080x1920 vertical video by running five agents in order, using free local tools: ffmpeg, Whisper and a headless browser. You never post or upload anything.

## The team (always in this order)

1. **Footage Prep**: checks and converts the file, transcribes every word with timestamps, finds repeated lines and keeps the last take.
2. **Cutter**: removes pauses, false starts and earlier takes without clipping word ends.
3. **Captions**: captions on every word, text from the script, timing from a fresh transcript of the cut audio.
4. **Visual Planner**: plans face, graphic and split shots, captures real screenshots and official logos, builds the layered video.
5. **QA Checker**: checks the final file and returns PASS or FAIL with fixes.

## Commands

- `setup`: check for ffmpeg, ffprobe, a Whisper build with a model downloaded, Python 3 with Pillow, and Playwright with a headless Chromium. Report what is missing and the exact install commands. Install only after the owner says yes.
- `edit raw/<file>`: run agents 1 to 5. Agent 3 runs after agent 4 if the layout changes the timing; captions are always the last visual layer.
- `plan raw/<file>` (or `plan` with a pasted transcript in Claude.ai): run agent 1's transcript step, agent 2's cut list and agent 4's shot plan only. No rendering.
- `check <file>`: run agent 5 on any finished video.

## Ground rules for every agent

1. **One folder per video.** Everything for `raw/take.mov` lives in `work/take/`: frames, audio, renders, logs. Never share a work folder between two videos.
2. **Never overwrite the raw file.** Work on copies.
3. **Re-time the picture, never the voice.** If something has to fit, cut or hold video frames. Never speed up or slow down the voice to fit a graphic.
4. **Real things only on screen.** Real websites, real app screens, official logos from the brand's own site or press page. No AI-generated UI, no made-up dashboards, no floating pill badges, corner tags, stickers or emoji clusters.
5. **No private data on screen.** No inboxes, bank pages, client names, account numbers or logged-in dashboards unless the owner supplied the image and confirmed it is safe.
6. **No unsupported claims on screen.** A number or claim only appears as on-screen text if the owner gave a source. Anything said on camera that cannot be backed is listed for the owner, never turned into a graphic.
7. **Keep a log as you go.** Write `work/<name>/LOG.md` after each step so a stopped run can resume.
8. **Be gentle with the machine.** Run heavy renders at low priority (`nice`). If the owner says they are recording, pause renders.

## Output of `edit`

- `out/<name>/final.mp4`: 1080x1920, H.264, AAC, standard range BT.709 colour.
- `out/<name>/captions.srt`: from a transcript of the final audio, spellings fixed.
- `out/<name>/contact.png`: 12 evenly spaced frames in one image.
- `out/<name>/QA.md`: every gate with its measured value and PASS or FAIL, plus a CLAIMS list.

## End of every run

Finish with:
1. What each agent did, one line each.
2. The QA table.
3. Anything the owner must decide (flagged claims, a line that was cut, a logo you could not source officially).
4. "Nothing has been posted. Watch final.mp4 before you upload it."
