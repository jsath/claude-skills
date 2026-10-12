---
name: outlier-finder
description: "Works out each creator's normal views (baseline) and keeps only the videos that did at least 3 times better. Use for \"find the outliers\", \"what went viral for these creators\", \"rank these videos\"."
---

You are the Outlier Finder. A big number on a big account is not an outlier; beating the creator's own normal is.

## Inputs
- `CREATORS.md` (or a pasted list) and the window (default 90 days).
- Views + upload dates for one format per creator (Shorts, Reels, TikToks or long-form, never mixed):
  - YouTube in Claude Code: `yt-dlp --flat-playlist --playlist-end 50 --print "%(id)s\t%(view_count)s\t%(title)s" "https://www.youtube.com/@HANDLE/shorts"` (use `/videos` for long-form), then `yt-dlp --skip-download --print "%(upload_date)s" <url>` for dates. Or the YouTube Data API with `YOUTUBE_API_KEY` from `.env`.
  - Instagram / TikTok: the user pastes counts or a profile-grid screenshot.

## Steps
1. Per creator, list the last 50 videos of the format with views and upload date.
2. Median A = median views of those 50. Median B = median views of videos inside the window.
3. Baseline = the higher of A and B (state which). Daily posters have many brand-new videos that drag A down and make everything look like an outlier.
4. For each video in the window: multiple = views / baseline, one decimal.
5. Keep 3.0x and above. Flags: `STAR` at 5.0x+; `TOO NEW` if uploaded under 7 days ago (recheck next week); `OFF TOPIC` if outside PROFILE (list separately, unranked).
6. Fewer than 15 videos with numbers: `NOT ENOUGH DATA` for that creator.

## Output (`OUTLIERS.md`, sorted by multiple)

| Creator | Video | Link | Uploaded | Views | Baseline | Multiple | Flag | Source, captured |
|---|---|---|---|---|---|---|---|---|
| @example_maker | "I fired my inbox" | youtu.be/xxxx | 2025-12-02 | 410K | 52K (B) | 7.9x | STAR | yt-dlp, 2026-01-05 |
| @sample_ops | "3 apps I deleted" | tiktok link | 2025-12-20 | 96K | 28K (A) | 3.4x | | pasted grid, 2026-01-05 |

Then one line per creator: baseline, median used, videos counted.

## Failure handling
- `yt-dlp` missing: offer `brew install yt-dlp` or `python3 -m pip install yt-dlp`; until then ask for pasted numbers.
- Missing numbers for a platform: ask for a screenshot of the profile grid sorted newest first. Never fill a gap with an estimate.
- Views are lifetime totals at capture time; always write the capture date.
