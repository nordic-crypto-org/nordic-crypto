#!/usr/bin/env python3
"""Update the description and thumbnail of a video that is already on YouTube.

Does not upload and does not insert a video. The request is videos.update with
part=snippet only, then thumbnails.set. The privacy setting and the scheduled
time are not read back into the request and are not sent.

The description is tools/youtube_upload.py's template, including the «Nettside:»
footer. The thumbnail is the issue poster already in newsletter/published/<id>/.

  python3 tools/youtube_metadata.py --issue 006 --video-id bvla1OX8FCU [--dry-run]

Auth: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (or --token-file). Never prints them.
A token whose scopes are only youtube.upload cannot replace a description; the script
stops before it changes anything and says what to re-consent. See docs/youtube-metadata.md.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from youtube_upload import ISSUES, access_token, description, find_issue

API = "https://www.googleapis.com/youtube/v3/"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/"
SNIPPET_UPDATE = API + "videos?part=snippet"
YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
# videos.update is not allowed with youtube.upload alone. thumbnails.set is listed
# with that scope, but a 403 after a successful insert is the phone-verification gate.
UPDATE_SCOPES = (
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtubepartner",
)
KEEP = ("title", "tags", "categoryId", "defaultLanguage", "defaultAudioLanguage")


class YoutubeError(RuntimeError):
    def __init__(self, code, body):
        self.code = code
        super().__init__(f"HTTP {code} {body}")
        self.body = body


def video_id_of(url):
    if not url:
        return None
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return (q.get("v") or [None])[0]


def snippet_body(video_id, snippet, new_description):
    """Body for videos.update. Allowlisted snippet fields plus the new description."""
    snippet = snippet or {}
    if "status" in snippet:
        raise RuntimeError("refusing to copy a status object into the snippet update")
    kept = {}
    for key in KEEP:
        value = snippet.get(key)
        if value not in (None, "", []):
            kept[key] = value
    if not kept.get("title"):
        raise RuntimeError("refusing to update: the current title is missing, and an empty title would replace it")
    if "categoryId" not in kept:
        kept["categoryId"] = "25"
    kept["description"] = new_description
    body = {"id": video_id, "snippet": kept}
    if set(body) != {"id", "snippet"} or "status" in body["snippet"]:
        raise RuntimeError("refusing to send anything except the snippet")
    return body


def scope_block(scopes):
    """None when the token may update a description. A string when it must not try."""
    if scopes is None:
        return None
    if set(scopes) & set(UPDATE_SCOPES):
        return None
    return (
        "The YouTube refresh token cannot update a video description. "
        "videos.update needs https://www.googleapis.com/auth/youtube "
        "or https://www.googleapis.com/auth/youtube.force-ssl "
        "(youtubepartner also works). The youtube.upload scope can insert a video and cannot replace the description. "
        "jQrgen: open the OAuth consent screen, grant those scopes, mint a new refresh token, and replace the "
        "youtube environment secret YT_REFRESH_TOKEN. Do not commit the token or paste it into a log. "
        "Custom thumbnails also need a phone-verified channel: https://www.youtube.com/verify "
        "(YouTube Studio → Settings → Channel → Feature eligibility). "
        "Run 42468185685 inserted bvla1OX8FCU and then thumbnails.set returned 403, which is that gate "
        "when the upload itself succeeded. Dispatching this workflow is a separate 403: "
        "GitHub's «Resource not accessible by integration» means the caller lacks Actions write. "
        "See docs/youtube-metadata.md."
    )


def explain_http_error(what, err):
    text = getattr(err, "body", str(err))
    code = getattr(err, "code", 0)
    low = (text or "").lower()
    lines = [f"{what} failed: HTTP {code} {(text or '')[:300]}"]
    if code == 403 and what == "thumbnail":
        lines.append(
            "Phone-verify @NordicCryptoTV at https://www.youtube.com/verify. "
            "YouTube refuses custom thumbnails until the channel is verified. "
            "A verified channel that still returns 403 needs a fresh refresh token with the youtube "
            "or youtube.force-ssl scope in the youtube environment secret YT_REFRESH_TOKEN. "
            "Do not commit the token. The description update, if it succeeded just above, did not change "
            "the privacy setting or the scheduled time; running this again sends the same description."
        )
    elif code == 403:
        lines.append(
            "This call needs the youtube or youtube.force-ssl scope. "
            "Replace YT_REFRESH_TOKEN in the youtube environment after re-consent. Do not commit the token."
        )
    if "insufficient" in low:
        lines.append("The token's scopes were rejected (insufficient permissions).")
    return " ".join(lines)


def token_scopes(at):
    """Scope list, or None when tokeninfo cannot be read. The access token is not logged."""
    url = "https://oauth2.googleapis.com/tokeninfo?access_token=" + urllib.parse.quote(at)
    try:
        info = json.load(urllib.request.urlopen(urllib.request.Request(url), timeout=30))
    except Exception:
        return None
    return [s for s in (info.get("scope") or "").replace(",", " ").split() if s]


def api(at, url, data=None, method="GET", content_type="application/json; charset=UTF-8"):
    headers = {"Authorization": "Bearer " + at}
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, body, headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()[:400].decode("utf-8", "replace")
        if at and at in raw:
            raw = raw.replace(at, "[token]")
        raise YoutubeError(e.code, raw) from None


def get_snippet(at, video_id):
    """Current snippet only. part=snippet, so the privacy and schedule are not even fetched."""
    got = api(at, API + "videos?part=snippet&id=" + urllib.parse.quote(video_id))
    items = got.get("items") or []
    if not items:
        raise YoutubeError(404, "video is not visible to this token")
    return items[0].get("snippet") or {}


def put_snippet(at, body):
    if set(body) != {"id", "snippet"}:
        raise RuntimeError("refusing to update anything except the snippet")
    return api(at, SNIPPET_UPDATE, body, "PUT")


def set_thumbnail(at, video_id, path):
    if not YT_ID.match(video_id or ""):
        raise RuntimeError("bad video id")
    ctype = "image/png" if str(path).lower().endswith(".png") else "image/jpeg"
    url = UPLOAD + "thumbnails/set?videoId=" + urllib.parse.quote(video_id)
    with open(path, "rb") as fh:
        return api(at, url, fh.read(), "POST", ctype)


def thumbnail_path(it, explicit):
    if explicit:
        return explicit
    poster = ((it.get("video") or {}).get("poster")) or "thumbnail.png"
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "newsletter", "published", it["id"], poster)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Update an existing video's description and thumbnail. Never uploads.")
    ap.add_argument("--issue", required=True, help="issue id, e.g. 006")
    ap.add_argument("--video-id", required=True, help="existing 11-character YouTube video id")
    ap.add_argument("--thumbnail", help="PNG or JPEG; default is the issue poster")
    ap.add_argument("--description", default="", help="override; default is the upload template")
    ap.add_argument("--token-file", default="~/.youtube_token_nordiccryptotv.json")
    ap.add_argument("--dry-run", action="store_true", help="print the description and change nothing")
    a = ap.parse_args(argv)

    if not YT_ID.match(a.video_id):
        sys.exit("video_id must be the 11-character YouTube id, not a URL and not a new upload")
    doc = json.loads(ISSUES.read_text())
    it = find_issue(doc, a.issue)
    recorded = video_id_of((it.get("video") or {}).get("youtube"))
    if recorded and recorded != a.video_id:
        sys.exit(f"refusing: issue {a.issue} is recorded as {recorded}, not {a.video_id}")
    text = a.description or description(it)
    thumb = thumbnail_path(it, a.thumbnail)
    if not os.path.isfile(thumb):
        sys.exit(f"thumbnail missing: {thumb}")
    if a.dry_run:
        print(f"dry run: PUT {SNIPPET_UPDATE} for {a.video_id}")
        print("The privacy setting and the scheduled time are left untouched. No video is uploaded.")
        print(f"thumbnail: {thumb}")
        print(text)
        return 0

    at = access_token(a.token_file)
    block = scope_block(token_scopes(at))
    if block:
        sys.exit(block)
    try:
        current = get_snippet(at, a.video_id)
        body = snippet_body(a.video_id, current, text)
        put_snippet(at, body)
    except YoutubeError as e:
        sys.exit(explain_http_error("description", e))
    print(f"description updated: https://www.youtube.com/watch?v={a.video_id}")
    try:
        set_thumbnail(at, a.video_id, thumb)
    except YoutubeError as e:
        sys.exit(explain_http_error("thumbnail", e))
    print(f"thumbnail set from {thumb}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as err:
        sys.exit(str(err))
