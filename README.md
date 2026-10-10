# Claude skills by @johannships

I build AI agents for companies, and I post the setups that actually work as
reels on [@johannships](https://johann.fyi/links). This repo is the Claude
side of that: every skill from my "Claude just killed..." videos, plus the
CLAUDE.md I run my own setup from, with the private bits taken out.

Everything here is free and MIT licensed. Take it, change it, ship it.

## What's inside

```
CLAUDE.md            my orchestrator setup as a template you can copy
skills/<name>/       one folder per skill
  SKILL.md           the skill Claude reads and follows
  agents/            one prompt per part (also works as Claude Code subagents)
skills/reels-engine  pointer to my reel editing engine (its own repo)
```

Every skill follows the same rules:

- **Drafts, not sends.** Nothing emails a client, posts, schedules live or moves
  money on its own. You approve every outgoing item and you press send.
- **No guessing.** Missing data becomes a question, never a made-up number.
  Every number says where it came from.
- **Works without connectors.** No Gmail or Slack hooked up? Paste the text or
  drop in a CSV export and it carries on.

## Install a skill

### Claude.ai (web, desktop, mobile)

1. Download the skill folder you want (for example `skills/warm-lead/`) and
   zip it, so the zip contains the folder with `SKILL.md` inside.
2. Make sure code execution is on in **Settings > Capabilities** (skills
   need it).
3. Go to **Customize > Skills** and upload the zip. On Team and Enterprise
   plans, your admin has to allow skills first.
4. Start a new chat and say what you want, or type `start`. Claude picks the
   skill up when the request matches its description.

Turn on the connectors a skill mentions (Settings > Connectors) if you have
them. If you don't, paste the data in.

### Claude Code

Copy the folder into your skills directory:

```bash
git clone https://github.com/johannships/claude-skills.git
cp -r claude-skills/skills/warm-lead ~/.claude/skills/
```

Use `~/.claude/skills/` for every project, or `.claude/skills/` inside one
project. Restart Claude Code, then ask for the job (or type `start`).

Want each part to run as a real subagent? Also copy the skill's `agents/`
files into `.claude/agents/`.

## The skills

| Skill | What it does | Reel |
|---|---|---|
| [raw-to-reel](skills/raw-to-reel) | Edits a raw talking-head take into a captioned vertical video in Claude Code | Claude just killed your video editor |
| [viral-breakdown](skills/viral-breakdown) | Finds videos that beat their creator's normal by 3x, explains why, adapts them | Claude just killed your competitor research |
| [ready-to-film](skills/ready-to-film) | Turns notes and voice memos into fact-checked scripts in your voice | Claude just killed your scriptwriter |
| [brand-deal-filter](skills/brand-deal-filter) | Labels sponsor pitches, checks the brand, reads the terms, drafts replies | Claude just killed your brand deals inbox |
| [content-multiplier](skills/content-multiplier) | Turns one long video into up to 30 clips and posts on a two-week plan | Claude just killed your repurposing workflow |
| [warm-lead](skills/warm-lead) | Cleans your lead list, researches each lead, drafts outreach and follow ups, sorts replies | Claude just killed cold outreach |
| [ops-desk](skills/ops-desk) | Writes your processes down, runs the morning check, drafts nudges, Friday wrap up | Claude just killed your operations manager |
| [new-hire](skills/new-hire) | Builds a two-week training plan, answers from your docs, quizzes, progress checks | Claude just killed your onboarding process |
| [happy-customer](skills/happy-customer) | Sorts the support inbox, builds an answer sheet, drafts replies, flags the hard ones | Claude just killed your customer support inbox |
| [monday-numbers](skills/monday-numbers) | Checks and compares your numbers, explains drops, gives three actions every Monday | Claude just killed your data analyst |
| [no-meeting-monday](skills/no-meeting-monday) | Collects updates, blockers and decisions into one Monday brief | Claude just killed your weekly meetings |
| [hand-it-off](skills/hand-it-off) | Finds the job you hate, maps it, and turns it into your own new Claude skill | Claude just killed the part of your business you hate the most |
| [launch-week](skills/launch-week) | Writes the sales page, launch emails and daily hooks, then a skeptic rewrites the hype | Claude just killed your launch strategy |
| [dm-closer](skills/dm-closer) | Builds your DM reply bank, qualifying questions and a ManyChat setup to run it | Claude just killed your DM strategy |
| [sounds-like-me](skills/sounds-like-me) | Learns how you write and talk, writes your voice guide, rewrites drafts to match | Claude just killed your brand voice guide |
| [caption-engine](skills/caption-engine) | Writes captions per platform in your voice, with a call to action that matches the video | Claude just killed your caption writer |
| [comment-reply](skills/comment-reply) | Pulls YouTube comments, sorts them, drafts replies, surfaces leads and video ideas | Claude just killed your comments section |
| [idea-bank](skills/idea-bank) | Turns your niche's outlier videos into a month of ideas you can talk about from experience | Claude just killed your ideas meeting |
| [best-time](skills/best-time) | Reads your own analytics exports and plans what to post, where and when | Claude just killed your posting schedule |
| [content-month](skills/content-month) | Sets your pillars and plans, writes and checks a month of posts | Claude just killed your content calendar |
| [daily-social](skills/daily-social) | Picks today's industry story and drafts posts for each platform, Friday report | Claude just killed your social media manager |
| [hiring-replacement](skills/hiring-replacement) | Lead intake, client onboarding, SOP tasks, weekly report and client replies | Claude just killed your entire hiring process |
| [bottleneck-removal](skills/bottleneck-removal) | Finds the process that waits on you most and turns it into a runbook | Claude just killed your business's biggest bottleneck |
| [founder-independence](skills/founder-independence) | Captures your head into a playbook, then decides, follows up and drafts from it | Claude just killed the reason your business needs you in it |
| [reels-engine](skills/reels-engine) | My full reel editing engine, in its own repo | The edits behind every reel |

## My setup: CLAUDE.md

[`CLAUDE.md`](CLAUDE.md) is the file my main Claude Code session runs from. It
is one orchestrator session that hands real work to subagents, keeps one
context file per project, holds a single NOW item, writes handoffs before any
session closes, and never quotes a number it has not measured. Copy it, fill
in the `<placeholders>`, and make it yours.

## Honest limits

- Skills run when you run them. Anything "every Monday" or "every morning"
  needs a scheduled task, where your plan supports one, or you typing the command.
- Connectors depend on your Claude plan and your admin. Every skill has a
  paste-or-export fallback.
- Video editing needs Claude Code on a computer. A Claude.ai chat cannot open
  or export video files.
- Check what your contracts and local privacy rules allow before you connect
  client inboxes or customer data.

## More

- Newsletter, twice a week, the repos and Claude setups I'm actually using:
  [johann.fyi/newsletter](https://johann.fyi/newsletter)
- Everything else: [johann.fyi/links](https://johann.fyi/links)

Found a bug or made one better? Open an issue or a pull request.
