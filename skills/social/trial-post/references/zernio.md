# Zernio payloads and responses (trial reels + TikTok)

Account ids below are placeholders: read yours with `accounts_list`. Field names follow Zernio's docs
(`docs_search` "trialParams", "tiktok_settings"); re-check them there if a call is rejected.

## Instagram Trial Reel: `call_tool` name `posts_create_post`
```json
{"content": "<IG caption, keyword CTA>",
 "media_items": [{"type": "video", "url": "https://media.zernio.com/temp/<file>.mp4"}],
 "platforms": [{"platform": "instagram", "accountId": "<IG_ACCOUNT_ID>",
                "platformSpecificData": {"trialParams": {"graduationStrategy": "MANUAL"}, "isAiGenerated": false}}],
 "publish_now": true,
 "timezone": "<Area/City>",
 "metadata": {"source": "trial-post", "plan": "<plan>"},
 "tags": ["trial-post"]}
```
- `graduationStrategy`: `MANUAL` (you graduate it in the app) or `SS_PERFORMANCE` (Instagram decides). Use MANUAL.
- For a slot instead of now: drop `publish_now`, add `"scheduled_for": "2026-11-02T18:05:00"` (local wall-clock, read
  in `timezone`).
- Do not send `is_draft`, `shareToFeed`, collaborators or paid-partnership fields.

Response to accept (shape seen on real posts): the post has an id and a status (`scheduled`, `publishing`,
`published`); the instagram target shows `platformSpecificData.trialParams.graduationStrategy: "MANUAL"`, and when
listed later `isTrialReel: true`, `trialGraduationStrategy: "MANUAL"`, plus `platformPostUrl` once published.
`isTrialReel` reflects how the post was created; the Instagram API exposes no trial field to read back, so on your
first day also open one trial in the app: it sits off your grid with a Trial label.

## TikTok public post
```json
{"content": "<TikTok caption: never the word comment; link in my bio>",
 "media_items": [{"type": "video", "url": "https://media.zernio.com/temp/<file>.mp4"}],
 "platforms": [{"platform": "tiktok", "accountId": "<TIKTOK_ACCOUNT_ID>"}],
 "publish_now": true, "timezone": "<Area/City>",
 "tiktok_settings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": true, "allow_duet": false,
                     "allow_stitch": false, "content_preview_confirmed": true, "express_consent_given": true,
                     "video_made_with_ai": false}}
```
- Add `"dry_run": true` to test a TikTok body without creating anything (answers `canPublish`).
- `video_made_with_ai: true` on any avatar or AI-generated footage.
- TikTok analytics (completion, For You share) fill in 24 to 48 h.

## Media upload
1. `call_tool` `media_get_media_presigned_url` `{"filename", "content_type": "video/mp4", "size"}` returns
   `uploadUrl` (a presigned storage URL, about 1 h) and `publicUrl`.
2. `curl -X PUT -H "Content-Type: video/mp4" --data-binary @file.mp4 "<uploadUrl>"` (HTTP 200, no auth header).
3. Download `publicUrl`, compare sha256. Temp files expire after about 7 days: upload again for older plans.

## Reading results (read-only)
- `posts_get` with the post id: status, platformPostUrl, trial fields.
- `analytics_get_analytics` with `post_id`: views, reach, shares, saves, `reelsSkipRate` (percent),
  `igReelsAvgWatchTime` (ms), `videoDurationSeconds`, TikTok `completionRate`. Instagram insights lag up to 48 h.
