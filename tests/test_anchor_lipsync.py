#!/usr/bin/env python3
"""Anders Fjell is lip-synced by one shared step. A still mouth fails the build.

python3 -m unittest tests.test_anchor_lipsync
"""
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "newsletter"))
import anchor_lipsync


def _content(issue):
    # 001 lives in 001-video-v2; every later issue is NNN-video.
    name = "001-video-v2" if issue == "001" else f"{issue}-video"
    path = os.path.join(ROOT, "newsletter", "issues", name, "content.py")
    spec = importlib.util.spec_from_file_location(f"content_{issue}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AnchorLipsync(unittest.TestCase):
    def test_a_still_mouth_fails_and_a_moving_mouth_passes(self):
        with self.assertRaises(SystemExit) as caught:
            anchor_lipsync.assert_mouth_moves(0.0, 0.0, "open_a")
        self.assertIn("Refusing to ship a still", str(caught.exception))
        with self.assertRaises(SystemExit):
            anchor_lipsync.assert_mouth_moves(9.0, 8.0)  # the whole frame drifted; the mouth did not lead
        anchor_lipsync.assert_mouth_moves(9.0, 0.2)

    def test_render_refuses_a_clip_that_was_not_checked(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as caught:
                anchor_lipsync.require_clip(d, "open_a")
            self.assertIn("Refusing the still", str(caught.exception))
            mp4, meta = anchor_lipsync.clip_paths(d, "open_a")
            with open(mp4, "wb") as fh:
                fh.write(b"x" * 2000)
            with open(meta, "w", encoding="utf-8") as fh:
                json.dump({"ok": False}, fh)
            with self.assertRaises(SystemExit):
                anchor_lipsync.require_clip(d, "open_a")
            with open(meta, "w", encoding="utf-8") as fh:
                json.dump({"ok": True}, fh)
            self.assertEqual(anchor_lipsync.require_clip(d, "open_a"), mp4)

    def test_anders_issues_declare_who_is_on_camera(self):
        for issue in ("004", "005", "006"):
            self.assertEqual(_content(issue).ON_CAMERA, ("anchor", "tonight", "story", "end"))
        for issue in ("001", "002", "003"):
            self.assertFalse(getattr(_content(issue), "ANCHOR_IMG", None))

    def test_renderers_have_no_still_fallback(self):
        for issue in ("004", "005", "006"):
            with open(os.path.join(ROOT, "newsletter", "issues", f"{issue}-video", "render.py"), encoding="utf-8") as fh:
                src = fh.read()
            self.assertIn("anchor_lipsync.Plate", src)
            self.assertNotIn("anchor_still", src)
            self.assertNotIn("has_clip", src)

    def test_no_per_issue_lipsync_script(self):
        issues = os.path.join(ROOT, "newsletter", "issues")
        found = []
        for dirpath, _dirs, files in os.walk(issues):
            if "lipsync.py" in files:
                found.append(os.path.join(dirpath, "lipsync.py"))
        self.assertEqual(found, [])

    def test_workflow_runs_the_shared_step_for_every_anchor_issue(self):
        with open(os.path.join(ROOT, ".github", "workflows", "newsreel-render.yml"), encoding="utf-8") as fh:
            yml = fh.read()
        self.assertIn("newsletter/anchor_lipsync.py", yml)
        self.assertIn("--check-rendered", yml)
        self.assertNotIn("if [ -f lipsync.py ]", yml)
        self.assertNotIn("hashFiles", yml)
        self.assertIn(anchor_lipsync.WAV2LIP_REV, yml)
        for rel, digest in anchor_lipsync.WEIGHTS.items():
            self.assertIn(digest, yml)
            self.assertIn(rel, yml)


if __name__ == "__main__":
    unittest.main()
