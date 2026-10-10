# Claude skills by @johannships

I build AI agents for companies and post the setups that work as reels on
[@johannships](https://johann.fyi/links). This repo is the Claude side of that:
the editing skills behind my own videos, the business and writing skills I
use day to day, every skill from my "Claude just killed..." reels, and the
CLAUDE.md my main session runs from. Private details are taken out.

Free and MIT licensed (humanizer keeps its own MIT licence, see below).

## What's inside

```
CLAUDE.md               my orchestrator setup, as a template to copy
skills/<name>/
  SKILL.md              what Claude reads and follows
  scripts/ or tools/    the code the skill runs (editing, SEO, security, PDF...)
  references/           deeper notes the skill loads when it needs them
  agents/               reel skills only: one prompt per part, usable as Claude Code subagents
```

## Install

**Claude Code** (needed for anything that touches video, scripts or a shell):

```bash
git clone https://github.com/jsath/claude-skills.git
cp -r claude-skills/skills/edit-style ~/.claude/skills/      # one skill
cp -r claude-skills/skills/* ~/.claude/skills/               # or all of them
```

Use `~/.claude/skills/` for every project or `.claude/skills/` for one. Start a
new session and ask for the job; Claude loads the skill when the request
matches its description. For the reel skills, copy `agents/*.md` into
`.claude/agents/` if you want each part to run as its own subagent.

**Claude.ai** (web, desktop, mobile): zip one skill folder so the zip contains
the folder with `SKILL.md` inside, turn on code execution in
**Settings > Capabilities**, then upload it under **Customize > Skills** (on
Team and Enterprise plans an admin has to allow skills first). Skills marked
"Code" below need Claude Code; a chat cannot open or export video files.

## The skills

### Editing: the pipeline behind my videos

Run in this order: transcribe, edit, write the post text, make the cover.

| Skill | What it does | Runs in |
|---|---|---|
| [edit-style](skills/edit-style) | Raw talking-head take to a finished 1080x1920 reel: layouts that switch per line, real UI and official logos, captions on every word, -14 LUFS voice, measured QA gates | Code |
| [longform-edit](skills/longform-edit) | Raw YouTube recording to a publish-ready video: retakes removed (last take kept), dead air tightened, mastered voice, captions throughout, chapters and description, gates on the final render | Code |
| [use-local-whisper](skills/use-local-whisper) | Local transcription with word timestamps (words.json, .txt, .srt). Nothing uploaded, no API key | Code |
| [reel-captions](skills/reel-captions) | Per-platform post captions for one finished video, with a checker for length, hashtags and where the CTA may go | Both |
| [thumbnail-generator](skills/thumbnail-generator) | 1280x720 thumbnail: text-free background, real cutout, words added in code, checked at phone size | Code |
| [script-polish](skills/script-polish) | Rewrites a script so it sounds like one person talking to one friend, with pacing checkpoints | Both |

### Business, writing and build skills

| Skill | What it does | Runs in |
|---|---|---|
| [humanizer](skills/humanizer) | Strips AI writing patterns from text. By [blader](https://github.com/blader/humanizer), MIT, copied unchanged with credit | Both |
| [tweet-writer](skills/tweet-writer) | X posts and threads in your voice, learned from your best posts, using formats that measured best | Both |
| [linkedin-writer](skills/linkedin-writer) | LinkedIn posts in your voice, formats ranked by measured reach | Both |
| [newsletter](skills/newsletter) | A founder newsletter issue in your voice: scene, lesson, one usable thing, one CTA | Both |
| [repo-radar](skills/repo-radar) | Keeps a verified, deduplicated list of GitHub repos you feature, with phone-size screenshots | Code |
| [technical-presentations](skills/technical-presentations) | Designs and red-teams technical talks and decks so they have depth, not framework cards | Both |
| [conversion-funnel-auditing](skills/conversion-funnel-auditing) | Audits a live funnel from ad promise to booked call or payment, with P0/P1/P2 findings | Both |
| [seo-agent](skills/seo-agent) | Site-config driven SEO audit and fix loop: crawl, indexability, schema, link graph, Core Web Vitals, Search Console, fixes as PRs | Code |
| [website-dev](skills/website-dev) | Ships changes to a GitHub + Vercel site and proves they are live | Code |
| [security-auditor](skills/security-auditor) | Repo security audit: secrets, dependency advisories, commit history, threat-model review, findings report | Code |
| [precision-pdf-editing](skills/precision-pdf-editing) | Surgical edits to an existing PDF that keep fonts, highlights and layout, with a pixel diff to prove it | Code |
| [downloadable-asset-engineering](skills/downloadable-asset-engineering) | Builds reproducible ZIP downloads and verifies the released bytes | Code |

### Skills from the reels ("Claude just killed...")

Each one runs five parts. Nothing sends, posts or schedules on its own: every
outgoing item is a draft you approve. Missing data becomes a question, never a
made-up number, and every skill has a paste-or-export fallback when a
connector is not available.

| Skill | What it does | Reel |
|---|---|---|
| [raw-to-reel](skills/raw-to-reel) | Simple five-step reel edit in Claude Code (prep, cut, captions, visuals, QA). For the full engine use edit-style | your video editor |
| [viral-breakdown](skills/viral-breakdown) | Finds videos that beat their creator's normal by 3x, explains why, ends in a weekly top five | your competitor research |
| [ready-to-film](skills/ready-to-film) | Notes and voice memos to fact-checked scripts in your voice | your scriptwriter |
| [brand-deal-filter](skills/brand-deal-filter) | Labels sponsor pitches, checks the brand, reads the terms, drafts replies | your brand deals inbox |
| [content-multiplier](skills/content-multiplier) | One long video into up to 30 clips and posts | your repurposing workflow |
| [warm-lead](skills/warm-lead) | Cleans a lead list, researches each lead, drafts outreach and follow-ups, sorts replies | cold outreach |
| [ops-desk](skills/ops-desk) | Writes processes down, morning check, nudge drafts, Friday wrap-up | your operations manager |
| [new-hire](skills/new-hire) | Two-week training plan, docs-only Q&A, quizzes, progress checks | your onboarding process |
| [happy-customer](skills/happy-customer) | Sorts the support inbox, builds an answer sheet, drafts replies, flags hard cases | your customer support inbox |
| [monday-numbers](skills/monday-numbers) | Checks and compares weekly numbers, explains drops, three Monday actions | your data analyst |
| [no-meeting-monday](skills/no-meeting-monday) | Updates, blockers and decisions in one Monday brief | your weekly meetings |
| [hand-it-off](skills/hand-it-off) | Maps the job you hate and writes it up as your own new Claude skill | the part of your business you hate the most |
| [launch-week](skills/launch-week) | Sales page, launch emails and daily hooks, then a skeptic rewrites the hype | your launch strategy |
| [dm-closer](skills/dm-closer) | DM reply bank, qualifying questions and a ManyChat flow plan | your DM strategy |
| [sounds-like-me](skills/sounds-like-me) | Learns how you write and talk, writes your voice guide, rewrites drafts | your brand voice guide |
| [caption-engine](skills/caption-engine) | Captions per platform in your voice, CTA matched to the video | your caption writer |
| [comment-reply](skills/comment-reply) | Pulls YouTube comments (Data API key or paste), sorts, drafts replies, finds leads and ideas | your comments section |
| [idea-bank](skills/idea-bank) | Outlier videos in your niche to a month of ideas you can speak to | your ideas meeting |
| [best-time](skills/best-time) | Reads your analytics exports and plans what to post, where and when | your posting schedule |
| [content-month](skills/content-month) | Pillars, then a planned, written and checked month of posts | your content calendar |
| [daily-social](skills/daily-social) | Picks today's industry story, drafts posts per platform, Friday report | your social media manager |
| [hiring-replacement](skills/hiring-replacement) | Lead intake, onboarding, SOP tasks, weekly report, client reply drafts | your entire hiring process |
| [bottleneck-removal](skills/bottleneck-removal) | Finds the process that waits on you most and turns it into a runbook | your business's biggest bottleneck |
| [founder-independence](skills/founder-independence) | Captures your head into a playbook, then decides, follows up and drafts from it | the reason your business needs you in it |
| [marketing-team](skills/marketing-team) | Voice guide, last month's numbers, a month plan and drafted posts | your marketing team |
| [podcast-repurpose](skills/podcast-repurpose) | One episode transcript to clip timestamps, show notes, chapters, a newsletter and posts | your podcast editor |
| [youtube-seo](skills/youtube-seo) | Reads your channel with your YouTube API key and drafts titles for new and old videos | your SEO strategy |
| [reels-engine](skills/reels-engine) | Pointer to my reel pipeline repo (ideation, scripting, Remotion panels) | the edits behind every reel |

## My setup: CLAUDE.md

[`CLAUDE.md`](CLAUDE.md) is the file my main Claude Code session runs from:
one orchestrator that hands real work to subagents, one context file per
project, a single NOW item, handoffs before any session closes, and no number
quoted unless it was measured. Copy it, fill in the `<placeholders>`, make it
yours.

## Honest limits

- Skills run when you run them. "Every Monday" means a scheduled task (where
  your plan has them, or `/schedule` in Claude Code) or you typing the command.
- Connectors depend on your plan and your admin.
- Editing skills need ffmpeg and a local Whisper; each one ships an install
  check and lists exactly what it needs.
- Check what your contracts and privacy rules allow before connecting client
  inboxes or customer data.

## More

- Newsletter, twice a week, with the repos and Claude setups I actually use:
  [johann.fyi/newsletter](https://johann.fyi/newsletter)
- Everything else: [johann.fyi/links](https://johann.fyi/links)

Found a bug or made one better? Open an issue or a pull request.
