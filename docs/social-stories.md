# Bluesky and Threads: new stories

`.github/workflows/social-stories.yml` runs `tools/social_stories.py` after every successful "Deploy site" and hourly at :07.

- **Bluesky** (@nordiccrypto.bsky.social): one post per new story, flag + English headline + story link, with a link card.
- **Threads** (@nordiccryptonews): one digest per Oslo day, same format as the X digest; a thread past 500 characters or 5 links.

Stories wait for their translations and a live page (Threads posts the ready ones from 18:00 Oslo; Bluesky posts an
untranslated story after 12 h). State is in the Actions cache; a missing cache only re-seeds. Manual dispatch is a dry run by default.

Repo secrets (a job without them skips with a notice):
- `BLUESKY_HANDLE` (`nordiccrypto.bsky.social`), `BLUESKY_APP_PASSWORD` (Bluesky → Settings → Privacy and security → App passwords)
- `THREADS_USER_ID`, `THREADS_ACCESS_TOKEN`: long-lived Threads user token with `threads_basic` and `threads_content_publish`.
  It lasts 60 days; refresh it with `GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=…` and update the secret.

Tests: `python3 -m unittest tests.test_social_stories`.
