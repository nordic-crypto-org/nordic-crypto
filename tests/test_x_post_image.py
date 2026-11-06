#!/usr/bin/env python3
"""tools/x_post_image.py: style rotation, prompts, brand overlay. No network."""
import io, json, os, random, sys, tempfile, unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import x_post_image as xi


class Styles(unittest.TestCase):
    def test_library_includes_ligne_claire_and_avoids_tintin(self):
        self.assertIn("ligne-claire", xi.STYLE_IDS)
        self.assertIn("photoreal-editorial", xi.STYLE_IDS)
        self.assertGreaterEqual(len(xi.STYLE_IDS), 10)
        blob = " ".join(xi.STYLE_PROMPT.values()).lower()
        self.assertNotIn("tintin", blob)
        self.assertNotIn("snowy", blob)
        self.assertNotIn("hergé", blob)
        self.assertNotIn("herge", blob)
        self.assertIn("ligne claire", blob)

    def test_pick_avoids_recent(self):
        recent = xi.STYLE_IDS[: xi.RECENT]
        rng = random.Random(0)
        for _ in range(20):
            s = xi.pick_style(recent, rng=rng)
            self.assertNotIn(s, recent)

    def test_remember_keeps_tail(self):
        out = []
        for s in xi.STYLE_IDS:
            out = xi.remember_style(out, s, keep=5)
        self.assertEqual(out, xi.STYLE_IDS[-5:])


class Prompts(unittest.TestCase):
    def test_story_prompt_has_style_and_no_banned(self):
        p = xi.story_prompt({"title_en": "Firi trading doubled", "summary": "Oslo exchange volume", "country": "NO"},
                            "ligne-claire")
        self.assertIn("ligne claire", p.lower())
        self.assertIn("Firi trading doubled", p)
        self.assertIn("Norway", p)
        self.assertNotIn("Tintin", p)
        self.assertNotIn("Nordic Crypto AS", p)
        self.assertIn("No readable text", p)

    def test_banned_scrub(self):
        p = xi.story_prompt({"title_en": "A Tintin fan meetup", "country": "BE"}, "cinematic-night")
        self.assertNotRegex(p, r"(?i)\btintin\b")


class Render(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_fallback_card_has_brand_top_right(self):
        from PIL import Image
        path = os.path.join(self.dir, "card.png")
        # force fallback by returning None from generator
        style, out = xi.render(
            {"title_en": "Virtune AI crypto index ETP", "source_name": "Kaupr", "country": "SE"},
            path, kind="news", style="photoreal-editorial",
            generator=lambda prompt: None,
        )
        self.assertEqual(style, "photoreal-editorial")
        im = Image.open(out)
        self.assertEqual(im.size, (1280, 720))
        # top-right region should contain teal brand plate pixels
        px = im.getpixel((1240, 40))
        self.assertEqual(px[:3], xi.TEAL)

    def test_ai_bytes_get_overlay(self):
        from PIL import Image
        # solid gold JPEG as fake AI output
        buf = io.BytesIO()
        Image.new("RGB", (640, 360), xi.GOLD).save(buf, "JPEG")
        path = os.path.join(self.dir, "ai.png")
        style, out = xi.render(
            {"title_en": "Norges Bank tokenisation", "country": "NO"},
            path, kind="news", style="watercolour",
            generator=lambda prompt: buf.getvalue(),
        )
        self.assertEqual(style, "watercolour")
        im = Image.open(out)
        self.assertEqual(im.size, (1280, 720))
        self.assertEqual(im.getpixel((1240, 40))[:3], xi.TEAL)

    def test_styles_state_roundtrip(self):
        path = os.path.join(self.dir, "ledger.json")
        with open(path, "w") as fh:
            json.dump({"posted": ["a"]}, fh)
        xi.save_styles(path, ["a", "b"])
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["posted"], ["a"])
        self.assertEqual(data["styles"], ["a", "b"])
        self.assertEqual(xi.load_styles(path), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
