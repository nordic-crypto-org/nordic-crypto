import io, os, sys, contextlib, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import x_newsletter as xn

META = {"id": "009", "number": 9, "title": "Nordic Crypto #9: Big week",
        "stories_list": [{"title": "T one", "summary": "", "url": "https://a.example/1"},
                         {"title": "T two", "summary": "", "url": "https://www.b.example/2/"}]}


class Text(unittest.TestCase):
    def test_url_counts_23(self):
        self.assertEqual(xn.x_len("a https://example.com/" + "x" * 200), 2 + 23)

    def test_parse_stories(self):
        h = ('<p style="m"><a href="https://a.example/1" style="font-weight:bold">T &amp; one</a> (original: x)<br>'
             'Sum one. Two. Three.<br><span>Src</span></p>')
        self.assertEqual(xn.parse_stories(h), [{"title": "T & one", "summary": "Sum one. Two. Three.", "url": "https://a.example/1"}])


class LongPost(unittest.TestCase):
    IDX = {"a.example/1": "https://nordiccrypto.no/stories/aaa/", "b.example/2": "https://nordiccrypto.no/stories/bbb/"}

    def test_shape(self):
        p = xn.build_long_post(META, xn.story_pages(META, self.IDX))
        self.assertEqual(p, "Nordic Crypto #9: Big week\nhttps://nordiccrypto.no/newsletter/009/\n\n"
                            "T one\nhttps://nordiccrypto.no/stories/aaa/\n\nT two\nhttps://nordiccrypto.no/stories/bbb/")

    def test_link_cap(self):
        meta = dict(META, stories_list=[{"title": f"S{i}", "url": f"https://s.example/{i}"} for i in range(30)])
        p = xn.build_long_post(meta, [f"https://nordiccrypto.no/stories/{i}/" for i in range(30)])
        self.assertEqual(len(xn.URL_RE.findall(p)), xn.MAX_URLS)
        self.assertTrue(p.endswith("More in the issue:\n" + "\n".join(f"S{i}" for i in range(xn.MAX_URLS - 1, 30))))

    def test_newest_issue_links_only_to_us(self):
        idx = xn.story_index()
        for m in [xn.load_issue()]:
            pages = xn.story_pages(m, idx)
            self.assertNotIn(None, pages, m["id"])
            p = xn.build_long_post(m, pages)
            self.assertTrue(p.startswith(f"Nordic Crypto #{m['number']}: "))
            self.assertIn(xn.issue_url(m), p.split("\n")[1])
            self.assertLessEqual(xn.x_len(p), xn.LONG_LIMIT)
            self.assertLessEqual(len(xn.URL_RE.findall(p)), xn.MAX_URLS)
            for u in xn.URL_RE.findall(p):
                self.assertTrue(u.startswith("https://nordiccrypto.no/"), u)
            for s in m["stories_list"][:xn.MAX_URLS - 1]:
                self.assertIn(s["title"], p)


class Run(unittest.TestCase):
    def setUp(self):
        self.saved = (xn.create_post, xn.upload_video, xn.is_live)

    def tearDown(self):
        xn.create_post, xn.upload_video, xn.is_live = self.saved
        for k in xn.ENV: os.environ.pop(k, None)

    def state(self, name):
        p = os.path.join(os.environ.get("TMPDIR", "/tmp"), name)
        if os.path.exists(p): os.remove(p)
        return p

    def test_dry_run_prints_and_never_posts(self):
        state = self.state("x_posted_test.json")
        xn.create_post = xn.upload_video = lambda *a, **k: self.fail("dry run must not call X")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(xn.main(["--issue", "2", "--dry-run", "--state", state]), 0)
        out = buf.getvalue()
        self.assertIn("# Issue 002", out)
        self.assertIn("one long post", out)
        self.assertIn("[+ video.mp4]", out)
        self.assertFalse(os.path.exists(state))

    def test_missing_secrets_skip(self):
        state = self.state("x_posted_test2.json")
        xn.create_post = lambda *a, **k: self.fail("must not post")
        self.assertEqual(xn.main(["--issue", "002", "--state", state]), 0)
        self.assertFalse(os.path.exists(state))

    def test_already_posted_is_skipped(self):
        state = self.state("x_posted_test3.json")
        xn.save_state(state, {"002": {"complete": True, "tweet_ids": ["1"]}})
        for k in xn.ENV: os.environ[k] = "x"
        xn.create_post = xn.is_live = lambda *a, **k: self.fail("must not touch X")
        self.assertEqual(xn.main(["--issue", "002", "--state", state]), 0)

    def test_posts_once_as_one_post(self):
        state = self.state("x_posted_test4.json")
        for k in xn.ENV: os.environ[k] = "x"
        calls = []
        xn.is_live = lambda url: True
        xn.create_post = lambda creds, text, reply_to=None, media_id=None: calls.append((text, reply_to)) or "42"
        self.assertEqual(xn.main(["--issue", "002", "--state", state, "--no-video"]), 0)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0][1])
        self.assertIn("https://nordiccrypto.no/stories/", calls[0][0])
        self.assertEqual(xn.load_state(state)["002"]["tweet_ids"], ["42"])

    def test_rejected_post_is_not_split(self):
        state = self.state("x_posted_test5.json")
        for k in xn.ENV: os.environ[k] = "x"
        calls = []
        xn.is_live = lambda url: True
        def reject(*a, **k):
            calls.append(1)
            raise RuntimeError("X API POST https://api.x.com/2/tweets -> 400: too long")
        xn.create_post = reject
        with self.assertRaises(RuntimeError):
            xn.main(["--issue", "002", "--state", state, "--no-video"])
        self.assertEqual(len(calls), 1)
        self.assertFalse(os.path.exists(state))

    def test_waits_for_story_pages(self):
        state = self.state("x_posted_test6.json")
        for k in xn.ENV: os.environ[k] = "x"
        xn.is_live = lambda url: "/stories/" not in url
        xn.create_post = lambda *a, **k: self.fail("must not post before story pages are live")
        self.assertEqual(xn.main(["--issue", "002", "--state", state, "--no-video"]), 0)


if __name__ == "__main__":
    unittest.main()
