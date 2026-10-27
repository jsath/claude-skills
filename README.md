# Claude skills by @johannships

I build AI agents for companies and post the setups that work as reels on
[@johannships](https://johann.fyi/links). This repo is the Claude side of that:
the editing skills behind my own videos, the business and writing skills I
use day to day, every skill from my "Claude just killed..." reels, and the
CLAUDE.md my main session runs from. Private details are taken out.

Free and MIT licensed (humanizer keeps its own MIT licence, see the writing folder).

## The full pipeline: idea -> script -> record -> "DJI is in" -> edit -> trial post -> scorecard

This is the whole content process I run, one skill per step. Install the eight folders below, record, plug the
camera card in, tell Claude "DJI is in" (any camera card works), and it gets the footage, sorts it, edits it and
posts the trial reels. You approve the ideas, film, and tap "Share to everyone" on the winners.

| # | Step | Skill | What you get | You do |
|---|---|---|---|---|
| 1 | Idea | [reel-ideation](skills/social/reel-ideation) | top creators in your niche, their recent virals with proof (likes, views, link, multiple of their own median), your voice-dictation dumps split into numbered ideas | pick the ideas |
| 2 | Script | [reel-ideation](skills/social/reel-ideation) + [script-polish](skills/video/script-polish) | word-for-word scripts copying a proven format (never its words), 3 hooks of different types each, both CTA endings, a RECORD-SHEET.md | answer the one-word questions |
| 3 | Record | RECORD-SHEET.md | the order to film in, slates to say, checks between setups | film |
| 4 | "DJI is in" | [footage-ingest](skills/video/footage-ingest) (uses [use-local-whisper](skills/video/use-local-whisper)) | clips copied and size-checked, audio == video on every clip, transcripts, takes matched to scripts, best takes picked, mirror + 30 fps conform, card ejected, TAKE-MAP.md | plug the card in |
| 5 | Edit | [edit-style](skills/video/edit-style) | 1080x1920 reels: face from frame 1, official logos, real UI, captions on every word, no dead air at joins, an Instagram ending and a link-in-bio ending, gates on the final files | look at the contact sheet |
| 6 | Captions | [reel-captions](skills/video/reel-captions) | per-platform post text, keyword CTA on Instagram only, bio line elsewhere, checked by a script | nothing |
| 7 | Trial post | [trial-post](skills/social/trial-post) | Instagram Trial Reels + TikTok via the Zernio MCP connector, every safety check, adapter for other schedulers | nothing |
| 8 | Scorecard | [reel-scorecard](skills/social/reel-scorecard) | at 72 h: which hook won each idea, what to graduate, kill or retire | tap "Share to everyone" on the winner |

Install just the pipeline (Claude Code):

```bash
git clone https://github.com/jsath/claude-skills.git
for s in social/reel-ideation video/script-polish video/footage-ingest video/use-local-whisper \
         video/edit-style video/reel-captions social/trial-post social/reel-scorecard; do
  cp -r "claude-skills/skills/$s" ~/.claude/skills/
done
```

What runs where: steps 1, 2, 6 and 8 work in any chat (Claude.ai or ChatGPT) if you paste links, numbers and
transcripts. Steps 4, 5 and 7 need Claude Code on the computer the card is plugged into: a chat app cannot read a
card, run ffmpeg or Whisper, or call the Zernio connector with the checks around it. Each skill lists its own
requirements and a setup check.

Setting this up for your own channel? Point your AI at this README and ask it to compare your current setup with
the table above, step by step, and install what is missing.

## What's inside
## What's inside

```
CLAUDE.md               my orchestrator setup, as a template to copy
categories.json         which folder each skill lives in (scripts/organize_skills.py reads it)
skills/<category>/<name>/   video, social, writing, business, web, dev
  SKILL.md              what Claude reads and follows
  scripts/ or tools/    the code the skill runs (editing, SEO, security, PDF...)
  templates/            starter files the skill copies into your folder
  references/           deeper notes the skill loads when it needs them
  agents/               reel skills only: one prompt per part, usable as Claude Code subagents
```

## Install

**Claude Code** (needed for anything that touches video, scripts or a shell):

```bash
git clone https://github.com/jsath/claude-skills.git
cp -r claude-skills/skills/video/edit-style ~/.claude/skills/   # one skill
cp -r claude-skills/skills/video/* ~/.claude/skills/            # one category
cp -r claude-skills/skills/*/* ~/.claude/skills/                # or all of them
```

Copy the skill folders themselves into `~/.claude/skills/`, not the category
folders: Claude Code looks for `~/.claude/skills/<name>/SKILL.md`.

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

Six folders, one per kind of job. Every skill keeps its own folder name, so
`johann.fyi/go/claude-skills?s=<name>` links still land on it.

<!-- skills:start -->

### Video: editing and repurposing (`skills/video/`)

The pipeline behind my videos runs in this order: footage-ingest ("the card is in": copy, sort, pick takes), use-local-whisper (transcribe), edit-style or longform-edit (edit), reel-captions (post text), thumbnail-generator (cover). Ideas, posting and the scorecard live in the social folder; the whole chain is in "The full pipeline" above.

| Skill | What it does | Runs in / from |
|---|---|---|
| [footage-ingest](skills/video/footage-ingest) | After a shoot: finds the camera or mic card, copies every clip with size checks, flags clips whose audio and video lengths differ, transcribes one at a time, matches takes to the record sheet by slate, picks the best take of each hook, body and ending, mirrors and conforms the picks, ejects safely. Never writes to the card | Code |
| [edit-style](skills/video/edit-style) | Raw talking-head take to a finished 1080x1920 reel: layouts that switch per line, real UI and official logos, face from frame 1, captions on every word, -14 LUFS voice, two CTA endings, measured QA gates incl. dead air and audio-envelope checks at every join | Code |
| [longform-edit](skills/video/longform-edit) | Raw YouTube recording to a publish-ready video: retakes removed (last take kept), dead air tightened, mastered voice, captions throughout, chapters and description, gates on the final render | Code |
| [use-local-whisper](skills/video/use-local-whisper) | Local transcription with word timestamps (words.json, .txt, .srt). Nothing uploaded, no API key | Code |
| [reel-captions](skills/video/reel-captions) | Per-platform post captions for one finished video, with a checker for length, hashtags and where the CTA may go | Both |
| [thumbnail-generator](skills/video/thumbnail-generator) | 1280x720 thumbnail: text-free background, real cutout, words added in code, checked at phone size | Code |
| [script-polish](skills/video/script-polish) | Rewrites a script so it sounds like one person talking to one friend, with pacing checkpoints | Both |
| [raw-to-reel](skills/video/raw-to-reel) | Simple five-step reel edit in Claude Code (prep, cut, captions, visuals, QA). For the full engine use edit-style | reel: "Claude just killed your video editor" |
| [ready-to-film](skills/video/ready-to-film) | Notes and voice memos to fact-checked scripts in your voice | reel: "Claude just killed your scriptwriter" |
| [caption-engine](skills/video/caption-engine) | Captions per platform in your voice, CTA matched to the video | reel: "Claude just killed your caption writer" |
| [content-multiplier](skills/video/content-multiplier) | One long video into up to 30 clips and posts | reel: "Claude just killed your repurposing workflow" |
| [podcast-repurpose](skills/video/podcast-repurpose) | One episode transcript to clip timestamps, show notes, chapters, a newsletter and posts | reel: "Claude just killed your podcast editor" |
| [reels-engine](skills/video/reels-engine) | Pointer to my reel pipeline repo (ideation, scripting, Remotion panels) | reel: "Claude just killed the edits behind every reel" |

### Social: ideas, planning and channels (`skills/social/`)

Most of these came from my "Claude just killed..." reels. Nothing posts on its own: every outgoing item is a draft you approve, except trial-post, which posts only reels that passed every gate, inside the rules in its SKILL.md.

| Skill | What it does | Runs in / from |
|---|---|---|
| [reel-ideation](skills/social/reel-ideation) | Top creators in your niche and their recent virals with proof (likes, views, link, multiple of the creator's median) via Agent Reach and yt-dlp; voice-dictation dumps to numbered ideas; full scripts copying a proven format with 3 hooks each, in a record sheet | Code (Both with pasted numbers) |
| [trial-post](skills/social/trial-post) | Instagram Trial Reels + TikTok through the Zernio MCP connector: the posts_create_post + trialParams path (never the feed-post trap), trial proof checked, spacing, caps, duplicate guard, STOP file; adapter for other schedulers | Code |
| [reel-scorecard](skills/social/reel-scorecard) | 72-hour read of the trials: which hook won each idea, what to graduate, kill or retire, same-source matched windows, weekly learning log | Code (Both with a CSV) |
| [viral-breakdown](skills/social/viral-breakdown) | Finds videos that beat their creator's normal by 3x, explains why, ends in a weekly top five | reel: "Claude just killed your competitor research" |
| [idea-bank](skills/social/idea-bank) | Outlier videos in your niche to a month of ideas you can speak to | reel: "Claude just killed your ideas meeting" |
| [best-time](skills/social/best-time) | Reads your analytics exports and plans what to post, where and when | reel: "Claude just killed your posting schedule" |
| [content-month](skills/social/content-month) | Pillars, then a planned, written and checked month of posts | reel: "Claude just killed your content calendar" |
| [daily-social](skills/social/daily-social) | Picks today's industry story, drafts posts per platform, Friday report | reel: "Claude just killed your social media manager" |
| [marketing-team](skills/social/marketing-team) | Voice guide, last month's numbers, a month plan and drafted posts | reel: "Claude just killed your marketing team" |
| [youtube-seo](skills/social/youtube-seo) | Reads your channel with your YouTube API key and drafts titles for new and old videos | reel: "Claude just killed your SEO strategy" |
| [comment-reply](skills/social/comment-reply) | Pulls YouTube comments (Data API key or paste), sorts, drafts replies, finds leads and ideas | reel: "Claude just killed your comments section" |
| [brand-deal-filter](skills/social/brand-deal-filter) | Labels sponsor pitches, checks the brand, reads the terms, drafts replies | reel: "Claude just killed your brand deals inbox" |
| [dm-closer](skills/social/dm-closer) | DM reply bank, qualifying questions and a ManyChat flow plan | reel: "Claude just killed your DM strategy" |

### Writing and voice (`skills/writing/`)

humanizer is by [blader](https://github.com/blader/humanizer), MIT, copied unchanged with credit.

| Skill | What it does | Runs in / from |
|---|---|---|
| [humanizer](skills/writing/humanizer) | Strips AI writing patterns from text. By [blader](https://github.com/blader/humanizer), MIT, copied unchanged with credit | Both |
| [sounds-like-me](skills/writing/sounds-like-me) | Learns how you write and talk, writes your voice guide, rewrites drafts | reel: "Claude just killed your brand voice guide" |
| [tweet-writer](skills/writing/tweet-writer) | X posts and threads in your voice, learned from your best posts, using formats that measured best | Both |
| [linkedin-writer](skills/writing/linkedin-writer) | LinkedIn posts in your voice, formats ranked by measured reach | Both |
| [newsletter](skills/writing/newsletter) | A founder newsletter issue in your voice: scene, lesson, one usable thing, one CTA | Both |
| [launch-week](skills/writing/launch-week) | Sales page, launch emails and daily hooks, then a skeptic rewrites the hype | reel: "Claude just killed your launch strategy" |
| [technical-presentations](skills/writing/technical-presentations) | Designs and red-teams technical talks and decks so they have depth, not framework cards | Both |
| [be-concise](skills/writing/be-concise) | The CLAUDE.md lines for short, answer-first replies, where they go (or Claude.ai's Instructions for Claude), with a before/after test | Both |

### Business: sales, ops and decisions (`skills/business/`)

Nothing sends, deletes or posts without you. Missing data becomes a question, never a made-up number.

| Skill | What it does | Runs in / from |
|---|---|---|
| [business-starter](skills/business/business-starter) | The four parts that make Claude know your business: an about-you CLAUDE.md, a context/ folder (pricing, offers, customers), a memory file of corrections, and skills/ | Both |
| [board-advisor](skills/business/board-advisor) | A brutally honest advisor: every idea gets the hard truth, steps to fix it, and a task you report back on | Both |
| [obsidian-brain](skills/business/obsidian-brain) | A free Obsidian vault of plain-text notes with Claude Code pointed at it: raw thoughts to clear ideas, half-finished notes finished, your originals untouched | Code |
| [spreadsheet-dashboard](skills/business/spreadsheet-dashboard) | Cleans a messy spreadsheet and builds a formula dashboard that updates with next month's rows, with a checker for the paste-new-rows trap and a public sample file | Both |
| [business-audit](skills/business/business-audit) | Web search for every listing, review and mention of your business, checked against the truth, then a P1/P2/P3 fix list and drafted replies and correction requests | Both |
| [warm-lead](skills/business/warm-lead) | Cleans a lead list, researches each lead, drafts outreach and follow-ups, sorts replies | reel: "Claude just killed cold outreach" |
| [meeting-follow-up](skills/business/meeting-follow-up) | After a call: verified attendee list, what was promised both ways, one owner per action, checks for replies and booked calls, then follow-up drafts. Never sends | Both |
| [competitor-research](skills/business/competitor-research) | Competitor deep dive from official sources first, every claim labelled with its evidence, ending in a claim-safe battlecard | Both |
| [ops-desk](skills/business/ops-desk) | Writes processes down, morning check, nudge drafts, Friday wrap-up | reel: "Claude just killed your operations manager" |
| [new-hire](skills/business/new-hire) | Two-week training plan, docs-only Q&A, quizzes, progress checks | reel: "Claude just killed your onboarding process" |
| [happy-customer](skills/business/happy-customer) | Sorts the support inbox, builds an answer sheet, drafts replies, flags hard cases | reel: "Claude just killed your customer support inbox" |
| [monday-numbers](skills/business/monday-numbers) | Checks and compares weekly numbers, explains drops, three Monday actions | reel: "Claude just killed your data analyst" |
| [no-meeting-monday](skills/business/no-meeting-monday) | Updates, blockers and decisions in one Monday brief | reel: "Claude just killed your weekly meetings" |
| [hand-it-off](skills/business/hand-it-off) | Maps the job you hate and writes it up as your own new Claude skill | reel: "Claude just killed the part of your business you hate the most" |
| [bottleneck-removal](skills/business/bottleneck-removal) | Finds the process that waits on you most and turns it into a runbook | reel: "Claude just killed your business's biggest bottleneck" |
| [founder-independence](skills/business/founder-independence) | Captures your head into a playbook, then decides, follows up and drafts from it | reel: "Claude just killed the reason your business needs you in it" |
| [hiring-replacement](skills/business/hiring-replacement) | Lead intake, onboarding, SOP tasks, weekly report, client reply drafts | reel: "Claude just killed your entire hiring process" |
| [safe-resale](skills/business/safe-resale) | Selling a valuable item: sold comps, net proceeds per channel as formulas, scam red flags, safe handover and shipping | Both |

### Websites and SEO (`skills/web/`)

| Skill | What it does | Runs in / from |
|---|---|---|
| [website-designer](skills/web/website-designer) | Claude Code + Anthropic's Frontend Design plugin + the 21st MCP: setup check, brief, one design direction, build, phone and desktop screenshot check | Code |
| [website-dev](skills/web/website-dev) | Ships changes to a GitHub + Vercel site and proves they are live | Code |
| [seo-agent](skills/web/seo-agent) | Site-config driven SEO audit and fix loop: crawl, indexability, schema, link graph, Core Web Vitals, Search Console, fixes as PRs | Code |
| [llms-txt](skills/web/llms-txt) | Reads your site, writes an llms.txt in the llmstxt.org format, checks it with an included validator, puts it live at /llms.txt. A proposal, not a ranking guarantee | Both |
| [conversion-funnel-auditing](skills/web/conversion-funnel-auditing) | Audits a live funnel from ad promise to booked call or payment, with P0/P1/P2 findings | Both |

### Dev, security and files (`skills/dev/`)

| Skill | What it does | Runs in / from |
|---|---|---|
| [security-auditor](skills/dev/security-auditor) | Repo security audit: secrets, dependency advisories, commit history, threat-model review, findings report | Code |
| [secure-credentials](skills/dev/secure-credentials) | API keys and tokens without the value ever reaching chat, logs or git: locked .env, read-only check, gitleaks, rotation checklist | Code |
| [linux-server-ops](skills/dev/linux-server-ops) | Disk full, out of memory or runaway logs on a Linux server: measure first, safest fixes first, prevention, before and after report | Code |
| [repo-radar](skills/dev/repo-radar) | Keeps a verified, deduplicated list of GitHub repos you feature, with phone-size screenshots | Code |
| [downloadable-asset-engineering](skills/dev/downloadable-asset-engineering) | Builds reproducible ZIP downloads and verifies the released bytes | Code |
| [precision-pdf-editing](skills/dev/precision-pdf-editing) | Surgical edits to an existing PDF that keep fonts, highlights and layout, with a pixel diff to prove it | Code |
| [html-to-pdf](skills/dev/html-to-pdf) | Documents as HTML with exact page layout, rendered to PDF headless, every page checked as an image. Tested render script included | Code |

<!-- skills:end -->

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
