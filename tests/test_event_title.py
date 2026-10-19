"""Event titles: page language first, original underneath; every event has a title in every site language."""
import json, os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import i18n
from tools import event_title as et, event_translate as tr

EV = {"id": "03951f33970c", "title": "Satoshi Nakamoto-årstalen 2027", "description": {"lang": "nb", "text": "x"}}


def all_events():
    out = {}
    for f in ("data/events.json", "archive/events.json", "data/events_backfill.json"):
        for e in json.load(open(os.path.join(ROOT, f), encoding="utf-8"))["events"]:
            out.setdefault(e["id"], e)
    return out.values()


class T(unittest.TestCase):
    def test_example(self):
        self.assertEqual(et.show(EV, "en"), ("Satoshi Nakamoto Annual Address 2027", "en", EV["title"]))
        self.assertEqual(et.show(EV, "nb"), (EV["title"], "nb", ""))
        head, lang, orig = et.show(EV, "fa")
        self.assertEqual((lang, orig), ("fa", EV["title"]))

    def test_changed_title_drops_translation(self):
        self.assertEqual(et.show(dict(EV, title="Ny tittel"), "en"), ("Ny tittel", "nb", ""))

    def test_editor_english_title_wins(self):
        e = {"id": "x", "title": "Crypto tax", "title_orig": "Kryptoskatt", "description": {"lang": "nb"}}
        self.assertEqual(et.show(e, "en", {}), ("Crypto tax", "en", "Kryptoskatt"))
        self.assertEqual(et.show(e, "de", {}), ("Crypto tax", "en", "Kryptoskatt"))

    def test_every_event_in_every_language(self):
        gaps = [(e["id"], et.missing(e)) for e in all_events() if et.missing(e)]
        self.assertEqual(gaps, [])
        for e in all_events():
            for lang in i18n.ALL_LANGS:
                self.assertTrue(et.show(e, lang)[0].strip())

    def test_fill_titles(self):
        cat, asked = {}, []
        def fake(title, src, langs):
            asked.append(langs)
            return {"lang": "nb", **{l: f"{l} title" for l in langs}}
        e = {"id": "n1", "title": "Ny tittel"}
        self.assertEqual(tr.fill_titles([e], cat, fake), ["n1"])
        self.assertEqual(cat["n1"]["lang"], "nb")
        self.assertNotIn("nb", cat["n1"])
        self.assertEqual(set(cat["n1"]) - {"source", "lang"}, set(i18n.ALL_LANGS) - {"nb"})
        self.assertEqual(tr.fill_titles([e], cat, fake), [])


if __name__ == "__main__":
    unittest.main()
