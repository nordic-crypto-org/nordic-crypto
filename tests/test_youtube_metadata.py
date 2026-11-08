#!/usr/bin/env python3
"""Metadata updates for a video that is already on YouTube. No network."""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import youtube_metadata
import youtube_upload


class Body(unittest.TestCase):
    def test_snippet_keeps_title_and_drops_schedule_fields(self):
        body = youtube_metadata.snippet_body(
            "bvla1OX8FCU",
            {"title": "Nordic Crypto #6: kept", "categoryId": "25", "tags": ["Nordic Crypto"],
             "publishedAt": "2026-11-08T09:41:06Z", "channelId": "UC", "description": "short"},
            "Nettside: https://nordiccrypto.no/\n",
        )
        self.assertEqual(set(body), {"id", "snippet"})
        self.assertEqual(body["snippet"]["title"], "Nordic Crypto #6: kept")
        self.assertIn("Nettside:", body["snippet"]["description"])
        self.assertNotIn("publishedAt", body["snippet"])
        self.assertNotIn("channelId", body["snippet"])
        self.assertNotIn("status", body)

    def test_put_url_is_snippet_only(self):
        seen = {}

        def fake(at, url, data=None, method="GET", content_type="application/json; charset=UTF-8"):
            seen.update(url=url, method=method, data=data)
            return {}

        saved = youtube_metadata.api
        youtube_metadata.api = fake
        try:
            body = youtube_metadata.snippet_body("bvla1OX8FCU", {"title": "Nordic Crypto #6: x", "categoryId": "25"}, "d")
            youtube_metadata.put_snippet("token-value", body)
        finally:
            youtube_metadata.api = saved
        self.assertEqual(seen["url"], "https://www.googleapis.com/youtube/v3/videos?part=snippet")
        self.assertEqual(seen["method"], "PUT")
        self.assertNotIn("status", seen["data"])

    def test_upload_scope_alone_is_refused(self):
        msg = youtube_metadata.scope_block(["https://www.googleapis.com/auth/youtube.upload"])
        self.assertIn("youtube.force-ssl", msg)
        self.assertIn("YT_REFRESH_TOKEN", msg)
        self.assertIn("verify", msg)
        self.assertIsNone(youtube_metadata.scope_block(["https://www.googleapis.com/auth/youtube.force-ssl"]))
        self.assertIsNone(youtube_metadata.scope_block(None))

    def test_description_template_has_nettside(self):
        import json
        doc = json.loads(youtube_upload.ISSUES.read_text())
        it = next(i for i in doc["issues"] if i["id"] == "006")
        text = youtube_upload.description(it)
        self.assertIn("Nettside:", text)
        self.assertIn("newsletter/006/", text)

    def test_dry_run_prints_the_template_and_does_not_upload(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(youtube_metadata.main(["--issue", "006", "--video-id", "bvla1OX8FCU", "--dry-run"]), 0)
        out = buf.getvalue()
        self.assertIn("Nettside:", out)
        self.assertIn("videos?part=snippet", out)
        self.assertIn("bvla1OX8FCU", out)
        self.assertIn("thumbnail.png", out)
        self.assertNotIn("videos.insert", out)

    def test_wrong_video_id_is_refused(self):
        with self.assertRaises(SystemExit) as ctx:
            youtube_metadata.main(["--issue", "006", "--video-id", "aaaaaaaaaaa", "--dry-run"])
        self.assertIn("aaaaaaaaaaa", str(ctx.exception))

    def test_source_never_inserts_or_sets_privacy(self):
        with open(youtube_metadata.__file__, encoding="utf-8") as fh:
            src = fh.read()
        for banned in ("videos.insert", "uploadType=resumable", "privacyStatus", "publishAt", "part=status", "part=snippet,status"):
            self.assertNotIn(banned, src, banned)

    def test_workflow_takes_video_id_and_does_not_upload(self):
        with open(os.path.join(ROOT, ".github/workflows/youtube-metadata.yml"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("video_id:", text)
        self.assertIn("environment: youtube", text)
        self.assertIn("actions: write", text)
        self.assertIn("tools/youtube_metadata.py", text)
        self.assertNotIn("youtube_upload.py", text)
        self.assertNotIn("--force", text)


class Force(unittest.TestCase):
    def test_force_does_not_upload_when_the_issue_has_a_video(self):
        saved = (youtube_upload.upload, youtube_upload.access_token)

        def boom(*a, **k):
            raise AssertionError("must not upload or refresh a token")

        youtube_upload.upload = boom
        youtube_upload.access_token = boom
        try:
            with self.assertRaises(SystemExit) as ctx:
                youtube_upload.main(["unused.mp4", "--issue", "006", "--force"])
        finally:
            youtube_upload.upload, youtube_upload.access_token = saved
        self.assertIn("second video", str(ctx.exception.code))
        self.assertIn("youtube_metadata.py", str(ctx.exception.code))


if __name__ == "__main__":
    unittest.main()
