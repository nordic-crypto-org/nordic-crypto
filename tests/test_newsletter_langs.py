"""Newsletter in every site language: Worker languages and texts, send copy, issue translation.
  python3 -m unittest tests.test_newsletter_langs"""
import json, os, re, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "newsletter")]
import i18n, send_issue as S
from tools import issue_translate as IT

LANGS = list(i18n.ALL_LANGS) + ([] if "se" in i18n.ALL_LANGS else ["se"])
JS = open(os.path.join(ROOT, "tipworker", "src", "messages.js"), encoding="utf-8").read()


def js_block(name):
    m = re.search(r"\nconst %s = \{(.*?)\n\};" % name, JS, re.S)
    return m.group(1)


class NewsletterLangs(unittest.TestCase):
    def test_worker_langs(self):
        nc = re.search(r'"nordic-crypto":\s*\{.*?langs:\s*\{(.*?)\}', JS, re.S).group(1)
        self.assertEqual(set(re.findall(r'(\w+):', nc)), set(LANGS))
        for name in ("T", "B"):
            keys = set(re.findall(r'^  (\w+): \{', js_block(name), re.M))
            self.assertTrue(set(LANGS) <= keys, f"{name} missing {set(LANGS) - keys}")

    def test_form_sends_page_language(self):
        os.environ.update(NC_NEWSLETTER="1", NEWSLETTER_ENDPOINT="https://w.test")
        import build
        for lang in ("se", "de", "ar"):
            build.LANG = lang
            self.assertIn(f'name="lang" value="{lang}"', build.newsletter_form())
        js = build.newsletter_script()
        self.assertIn("j.error==='lang'", js)
        self.assertIn("subscribed/", js)

    def test_send_copy(self):
        self.assertEqual(set(S.LANGS), set(LANGS))
        self.assertTrue(set(LANGS) <= set(S.COPY))
        for lang in LANGS:
            c = S.COPY[lang]
            self.assertTrue(all(c[k] for k in ("read", "unsub", "why")), lang)
            self.assertIn("Nordic Crypto", c["why"], lang)
        html_ar, _ = S.compose("<p>x</p>", "ar", "https://nordiccrypto.no/ar/newsletter/001/", "https://w.test/u", "s")
        self.assertIn('dir="rtl"', html_ar)
        self.assertIn(S.COPY["ar"]["unsub"], html_ar)
        html_de, text_de = S.compose("<p>Bis bald,<br>Das Nordic Crypto-Team</p>", "de", "", "", "s")
        self.assertNotIn('dir="rtl"', html_de)
        self.assertNotIn(S.SIGN_OFF, html_de + text_de, "translated sign-off is not repeated in English")

    def test_issue_translate(self):
        src = ('<p style="a">Hello <a href="https://x.test/">world</a></p><p>2026</p>'
               '<p style="b">The Nordic Crypto team</p><li>Second line</li>')
        segs = IT.segments(src)
        self.assertEqual([k for k, _ in segs], ["0", "3"])
        self.assertEqual(IT.rebuild(src, {}), src)
        fake = lambda prompt, payload: {k: "DE " + v for k, v in json.loads(payload).items()}
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "001"))
            open(os.path.join(tmp, "001", "issue.html"), "w").write(src)
            open(os.path.join(tmp, "001", "issue.nb.html"), "w").write("keep")
            json.dump({"issues": [{"id": "001", "lang": "en", "title": "Issue one", "subtitle": "Week one",
                                   "title_i18n": {"nb": "Utgave en"}}]}, open(os.path.join(tmp, "issues.json"), "w"))
            valid, IT.st.valid = IT.st.valid, lambda *a: ""
            try:
                IT.run(langs=["de", "nb"], translate=fake, log=lambda *_: None, pub=tmp)
            finally:
                IT.st.valid = valid
            de = open(os.path.join(tmp, "001", "issue.de.html")).read()
            self.assertIn('<p style="a">DE Hello <a href="https://x.test/">world</a></p>', de)
            self.assertIn("<li>DE Second line</li>", de)
            self.assertIn(">The Nordic Crypto team<", de)
            self.assertEqual(open(os.path.join(tmp, "001", "issue.nb.html")).read(), "keep")
            meta = json.load(open(os.path.join(tmp, "issues.json")))["issues"][0]
            self.assertEqual(meta["title_i18n"], {"nb": "Utgave en", "de": "DE Issue one"})
            self.assertEqual(meta["subtitle_i18n"]["de"], "DE Week one")


if __name__ == "__main__":
    unittest.main()
