#!/usr/bin/env python3
"""Northern Sami MT helper: masking, checks and pipeline routing, offline."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import sami_mt, story_translate, event_translate


class SamiMT(unittest.TestCase):
    def test_mask_round_trip(self):
        src = 'See <a href="/about/">the page</a>, {n} stories &amp; $b<br>.'
        masked, toks, opened = sami_mt.mask(src)
        self.assertNotIn("{n}", masked)
        self.assertEqual(sami_mt.unmask(masked, toks, opened), src)
        self.assertIsNone(sami_mt.unmask(masked.replace("⟦0⟧", ""), toks, opened))

    def test_check(self):
        self.assertTrue(sami_mt.check("Nordic Crypto is a news site.", "Nordic Crypto lea ođassiidu."))
        self.assertFalse(sami_mt.check("Nordic Crypto is a news site.", "Ođassiidu."))
        self.assertFalse(sami_mt.check("The proposal has since been shelved by the government.",
                                       "The proposal has since been shelved by the government. Ráđđehus dieđiha."))

    def test_story_se_goes_to_sami(self):
        item = {"id": "x", "title": "T", "title_en": "Headline here", "summary": "One. Two.", "language": "English"}
        fake_model = lambda system, user: (_ for _ in ()).throw(AssertionError("model called for se"))
        got = story_translate.translate_story(item, {"se": ["headline", "summary"]}, "", fake_model, lambda m: None,
                                              sami=lambda texts, src, alt=None: [f"se:{t}" for t in texts])
        self.assertEqual(got["se"], {"headline": "se:Headline here", "summary": "se:One. Two."})

    def test_event_se_from_english_when_source_unsupported(self):
        seen = []
        def sami(texts, src, alt=None):
            seen.append(src); return ["Sámegiel teaksta"]
        out = event_translate._sami(sami, "Svensk text", "sv", {"en": "English text"})
        self.assertEqual((out, seen), ("Sámegiel teaksta", ["en"]))


if __name__ == "__main__":
    unittest.main()
