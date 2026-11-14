# YouTube metadata for an existing video

`tools/youtube_metadata.py` updates a video that is already on @NordicCryptoTV.

- `PUT videos?part=snippet` replaces `snippet.description` with the template in `tools/youtube_upload.py`, including the «Nettside:» line. The current title, tags and category are kept.
- `POST thumbnails/set` sets `newsletter/published/<id>/thumbnail.png`.
- The privacy setting and the scheduled time are not sent. Nothing is uploaded. `--force` on `tools/youtube_upload.py` now refuses when that issue already has a video, because it would upload a second one.

```sh
python3 tools/youtube_metadata.py --issue 006 --video-id bvla1OX8FCU --dry-run
```

## What failed on #6

`bvla1OX8FCU` (public 9 Nov 2026 09:30 Europe/Oslo, `2026-11-09T08:30:00Z`) was inserted by run [42468185685](https://github.com/nordic-crypto-org/nordic-crypto/actions/runs/42468185685). The log line was `thumbnail failed: HTTP 403`. The insert succeeded, so the refresh token can upload. The description on the video is the short one from `tools/youtube_meta.py`, which has no «Nettside:» line. The render lint treats «Nettside» as non-English, so that template stays on the render path. This job is the one that writes the upload template onto a video that is already there.

## 403 on thumbnails.set

YouTube's message for this 403 is that the authenticated user cannot upload and set custom video thumbnails. After a successful `videos.insert`, that is the phone-verification gate, not a failed upload.

jQrgen, before a real metadata run:

1. Phone-verify @NordicCryptoTV at <https://www.youtube.com/verify> (YouTube Studio → Settings → Channel → Feature eligibility). Confirm a custom thumbnail can be set by hand on the video. YouTube can take a while to unlock the feature after verification.
2. Re-consent the OAuth client with `https://www.googleapis.com/auth/youtube` and `https://www.googleapis.com/auth/youtube.force-ssl`. `videos.update` (the description) is not allowed with only `youtube.upload`. `thumbnails.set` is documented with `youtube.upload` as well, and this channel's 403 still matches an unverified channel. A new refresh token covers both.
3. Put the new refresh token in the `youtube` environment secret `YT_REFRESH_TOKEN`. Leave the client id and secret unless the client changed. Do not commit the token or paste it into a log or a pull request.

The script reads the token's scopes and exits before it changes anything when the description cannot be updated. A thumbnail 403 after the description was written does not change the privacy setting or the scheduled time. Running the job again sends the same description and retries the thumbnail.

## 403 «Resource not accessible by integration» on the trigger

That string is GitHub, not YouTube. `POST /repos/.../actions/workflows/.../dispatches` returns it when the token is a GitHub App or `GITHUB_TOKEN` without permission to write Actions.

- Dispatch from the Actions tab while logged in. That uses your user permission.
- A workflow or a GitHub App that should dispatch this needs the Actions permission (read and write) on this repository, and the calling workflow needs `permissions: actions: write`.
- Settings → Actions → General → Workflow permissions must be "Read and write permissions" when the caller is `GITHUB_TOKEN`. A read-only default overrides `actions: write` in the YAML, and the API still returns this 403.
- `workflow_dispatch` exists only once this file is on `main`.

`YouTube metadata`, `YouTube newsletter upload` and `YouTube video upload` declare `actions: write` for their own job token. That does not grant the same permission to whoever starts the run.

## Rerun #6 after this is on main

Do this only after the merge. A dry run is the default.

```sh
gh workflow run "YouTube metadata" --ref main \
  -f issue=006 -f video_id=bvla1OX8FCU -f dry_run=false
```

Or: Actions → YouTube metadata → Run workflow, branch `main`, issue `006`, video id `bvla1OX8FCU`, dry run off.
