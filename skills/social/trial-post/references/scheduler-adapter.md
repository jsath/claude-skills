# SCHEDULER ADAPTER: using another tool next to (or instead of) Zernio

## What any scheduler must give you before it posts a reel for this pipeline
| need | why | if missing |
|---|---|---|
| Instagram Trial Reels (MANUAL graduation) | the whole hook test depends on non-followers seeing it first | use it for the main feed only, keep trials on Zernio |
| per-platform caption | keyword CTA on Instagram, bio line elsewhere | do not use it for keyword reels |
| per-platform video file | `final.mp4` on Instagram, `final-bio.mp4` elsewhere | do not use it for keyword reels |
| future-dated schedule + a read-back of the queue | you can review and cancel before it goes live | schedule only by hand |
| AI-content flag | avatar footage must carry the platform's own AI label | no avatar footage through it |
| no "post now" by default | a scheduler is a review window | set the rule in your CLAUDE.md |

## Worked example: Metricool (main feed, graduated winners)
- Use Metricool for the MAIN feed: a new reel made from a winning trial idea or hook, future-dated, never post-now.
- Never upload the same trial file again through Metricool (duplicate content splits engagement); post a new cut.
- Dry run first: print the exact payload, wait for the creator's yes, then write, then read the queue back.
- LinkedIn and X: drafts only, the creator posts those by hand.

## <YOUR SCHEDULER> (fill this in)
- Name and how Claude reaches it (MCP connector, API key in a local .env that never enters chat, browser):
- Can it make Instagram Trial Reels? (yes / no / unknown: test with one post and check the app)
- Exact create call and the response field that proves the post type:
- Per-platform captions and files: how:
- AI flag field:
- Queue read-back call:
- What it must never do (post now, other accounts, DMs, deletes):
