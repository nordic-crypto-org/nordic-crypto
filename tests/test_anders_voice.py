#!/usr/bin/env python3
"""Anders Fjell uses the free male Norwegian edge-tts voice (nb-NO-FinnNeural).

python3 -m unittest tests.test_anders_voice
"""
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Issues where Anders is on camera. 001–003 have no Anders plate and are unchanged.
ANDERS_ISSUES = ("004", "005", "006")
ANDERS_VOICE = "nb-NO-FinnNeural"


def _content(issue):
    path = os.path.join(ROOT, "newsletter", "issues", f"{issue}-video", "content.py")
    spec = importlib.util.spec_from_file_location(f"content_{issue}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AndersVoice(unittest.TestCase):
    def test_configured_voice_is_nb_no_male(self):
        for issue in ANDERS_ISSUES:
            voice = _content(issue).VOICE
            self.assertEqual(voice, ANDERS_VOICE, f"issue {issue}")
            self.assertTrue(voice.startswith("nb-NO-"), f"issue {issue} locale")
            self.assertTrue(voice.endswith("FinnNeural"), f"issue {issue} must be the male Finn voice")

    def test_anchor_plate_is_present(self):
        for issue in ANDERS_ISSUES:
            content = _content(issue)
            path = os.path.join(
                ROOT, "newsletter", "issues", f"{issue}-video", content.ANCHOR_IMG
            )
            self.assertTrue(os.path.isfile(path), path)
            self.assertGreater(os.path.getsize(path), 50_000, path)


if __name__ == "__main__":
    unittest.main()
