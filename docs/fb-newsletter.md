# Newsletter → Facebook Page video post

`tools/fb_newsletter.py` posts each new weekly Nordic Crypto issue to the Nordic Crypto Facebook Page, once, as a
single video post (Graph API `POST /{page-id}/videos`).

- **Video:** by default it passes `file_url` (the issue's `video.url`), so Facebook fetches the MP4 itself. With
  `--upload`, or when there is no `video.url`, the MP4 bytes are sent as `source` (local `video.mp4` or the
  sha256-checked download).
- **Title:** `Nordic Crypto #N: <headline>`.
- **Description:** the intro, the issue link, every story (headline, 1–2 sentence summary, link) and the archive link.
- A real run only posts once `https://nordiccrypto.no/newsletter/<id>/` answers 200.
- **State:** `data/fb_posted.json` (issue id → video id). A posted issue is never posted again.

```sh
python3 tools/fb_newsletter.py --dry-run             # newest issue, print only
python3 tools/fb_newsletter.py --issue 002 --dry-run
python3 -m pytest tests/test_fb_newsletter.py
```

## Secrets
`FB_PAGE_ID` and `FB_PAGE_ACCESS_TOKEN` (a long-lived Page token for a Meta app with `pages_manage_posts`,
`pages_read_engagement` and `publish_video`). If either is missing, the script logs `skipping: missing …` and exits 0.

## CI
`.github/workflows/fb-newsletter.yml` runs after each successful "Deploy site", every 30 minutes on Monday mornings,
and on manual dispatch (`issue`, `dry_run`). It commits `data/fb_posted.json` back to `main`.

## Covers
The newsreels open on a black frame, so a platform that picks frame 0 shows a black thumbnail.
- Facebook: the issue poster (`thumbnail.png`) is sent as `thumb`.
- Instagram: `tools/ig_newsletter.py` posts the Reel with `cover_url` = `nordiccrypto.no/newsletter/<id>/thumbnail-vertical.png`
  (`VERTICAL=1 python3 render.py thumb`, copy it into `newsletter/published/<id>/`; `build.py` publishes it). If it is not
  live, it falls back to `thumb_offset` 2000 ms. Env: `IG_USER_ID`, `FB_PAGE_ACCESS_TOKEN`. State: `data/ig_posted.json`.
- YouTube: `tools/youtube_upload.py --thumbnail thumbnail.png` (unchanged).

A published Reel's cover cannot be changed through the Graph API; change it in the Instagram app (Edit → Edit cover).
