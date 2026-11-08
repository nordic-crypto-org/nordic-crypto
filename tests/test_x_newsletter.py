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

    def test_every_story_is_linked(self):
        meta = dict(META, stories_list=[{"title": f"S{i}", "url": f"https://s.example/{i}"} for i in range(30)])
        pages = [f"https://nordiccrypto.no/stories/{i}/" for i in range(30)]
        p = xn.build_long_post(meta, pages)
        self.assertEqual(len(xn.URL_RE.findall(p)), 31)
        self.assertNotIn("More in the issue", p)
        for i in range(30):
            self.assertIn(f"S{i}\nhttps://nordiccrypto.no/stories/{i}/", p)

    def test_missing_page_is_not_dropped(self):
        with self.assertRaises(RuntimeError) as ctx:
            xn.build_long_post(META, ["https://nordiccrypto.no/stories/aaa/", None])
        self.assertIn("without a link", str(ctx.exception))

    def test_over_limit_does_not_drop_stories(self):
        meta = dict(META, stories_list=[{"title": "S" * 40, "url": "https://s.example/x"} for _ in range(8)])
        pages = ["https://nordiccrypto.no/stories/x/"] * 8
        old = xn.LONG_LIMIT
        xn.LONG_LIMIT = 80
        try:
            with self.assertRaises(RuntimeError) as ctx:
                xn.build_long_post(meta, pages)
        finally:
            xn.LONG_LIMIT = old
        self.assertIn("refusing to drop", str(ctx.exception))

    def test_newest_issue_links_only_to_us(self):
        idx = xn.story_index()
        for m in [xn.load_issue()]:
            pages = xn.story_pages(m, idx)
            self.assertNotIn(None, pages, m["id"])
            p = xn.build_long_post(m, pages)
            self.assertTrue(p.startswith(f"Nordic Crypto #{m['number']}: "))
            self.assertIn(xn.issue_url(m), p.split("\n")[1])
            self.assertLessEqual(xn.x_len(p), xn.LONG_LIMIT)
            self.assertEqual(len(xn.URL_RE.findall(p)), 1 + len(m["stories_list"]))
            for u in xn.URL_RE.findall(p):
                self.assertTrue(u.startswith("https://nordiccrypto.no/"), u)
            for s in m["stories_list"]:
                self.assertIn(s["title"], p)


class Run(unittest.TestCase):
    def setUp(self):
        self.saved = (xn.create_post, xn.upload_video, xn.upload_image, xn.is_live,
                      xn.account_username, xn.prepare_issue_image, xn.assert_brand_account)

    def tearDown(self):
        (xn.create_post, xn.upload_video, xn.upload_image, xn.is_live,
         xn.account_username, xn.prepare_issue_image, xn.assert_brand_account) = self.saved
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
        self.assertIn("[+ issue image", out)
        self.assertNotIn("[+ video.mp4]", out)
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
        xn.create_post = xn.is_live = xn.assert_brand_account = lambda *a, **k: self.fail("must not touch X")
        self.assertEqual(xn.main(["--issue", "002", "--state", state]), 0)

    def test_partial_row_is_also_a_duplicate(self):
        state = self.state("x_posted_partial.json")
        xn.save_state(state, {"002": {"tweet_ids": ["9"], "url": "https://x.com/nordiccryptobot/status/9"}})
        for k in xn.ENV: os.environ[k] = "x"
        xn.create_post = xn.prepare_issue_image = lambda *a, **k: self.fail("must not post again")
        self.assertEqual(xn.main(["--issue", "002", "--state", state, "--no-video"]), 0)

    def _ready(self):
        for k in xn.ENV: os.environ[k] = "x"
        xn.is_live = lambda url: True
        xn.account_username = lambda creds: "nordiccryptobot"
        xn.prepare_issue_image = lambda meta: {
            "path": os.path.join(os.environ.get("TMPDIR", "/tmp"), "nc-issue-test.png"),
            "style_id": "cyanotype-default", "kind": "ai",
            "url": "https://api.nordiccrypto.no/story-images/newsletter-002.png"}
        open(xn.prepare_issue_image({})["path"], "wb").write(b"png")
        xn.upload_image = lambda creds, path: "img1"
        xn.upload_video = lambda *a, **k: self.fail("the newsreel is not uploaded to X")

    def test_posts_once_as_one_post(self):
        state = self.state("x_posted_test4.json")
        self._ready()
        calls = []
        def create(creds, text, reply_to=None, media_id=None, media_ids=None):
            calls.append((text, reply_to, media_ids))
            return "42"
        xn.create_post = create
        self.assertEqual(xn.main(["--issue", "002", "--state", state, "--no-video"]), 0)
        self.assertEqual(len(calls), 1)
        self.assertIsNone(calls[0][1])
        self.assertEqual(calls[0][2], ["img1"])
        self.assertIn("https://nordiccrypto.no/stories/", calls[0][0])
        self.assertNotIn("https://x.com/jQrgensn", calls[0][0])
        row = xn.load_state(state)["002"]
        self.assertEqual(row["tweet_ids"], ["42"])
        self.assertTrue(row["url"].startswith("https://x.com/nordiccryptobot/status/"))
        self.assertEqual(row["image_style"], "cyanotype-default")

    def test_refuses_other_account(self):
        state = self.state("x_posted_other.json")
        self._ready()
        xn.account_username = lambda creds: "jQrgensn"
        xn.create_post = lambda *a, **k: self.fail("must not post as another account")
        with self.assertRaises(RuntimeError) as ctx:
            xn.main(["--issue", "002", "--state", state, "--no-video"])
        self.assertIn("@jQrgensn", str(ctx.exception))
        self.assertIn("nordiccryptobot", str(ctx.exception))
        self.assertFalse(os.path.exists(state))

    def test_rejected_post_is_not_split(self):
        state = self.state("x_posted_test5.json")
        self._ready()
        calls = []
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
        xn.create_post = xn.prepare_issue_image = lambda *a, **k: self.fail("must not post before story pages are live")
        self.assertEqual(xn.main(["--issue", "002", "--state", state, "--no-video"]), 0)

    def test_release_download_retries_502(self):
        import io as _io
        import urllib.error
        calls = {"n": 0, "urls": []}

        class Body:
            def __init__(self, data):
                self.data = data
            def read(self):
                return self.data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def opener(req, timeout):
            calls["n"] += 1
            calls["urls"].append(req.full_url)
            if calls["n"] == 1:
                raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", {}, _io.BytesIO(b""))
            return Body(b"mp4-bytes")

        dest = self.state("video.bin")
        url = "https://github.com/nordic-crypto-org/nordic-crypto/releases/download/newsletter-006-newsreel-1/nordic-crypto-6-newsreel.mp4"
        os.environ["GH_TOKEN"] = "super-secret-token-value"
        try:
            buf = _io.StringIO()
            with contextlib.redirect_stderr(buf):
                xn.download_url(url, dest, token=None, attempts=3, sleep=lambda s: None, opener=opener)
            self.assertEqual(open(dest, "rb").read(), b"mp4-bytes")
            self.assertEqual(calls["n"], 2)
            self.assertIn("502", buf.getvalue())
            self.assertNotIn("super-secret-token-value", buf.getvalue())
        finally:
            os.environ.pop("GH_TOKEN", None)

    def test_release_download_prefers_the_api(self):
        calls = []

        class Body:
            def __init__(self, data):
                self.data = data
            def read(self):
                return self.data
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        def opener(req, timeout):
            calls.append(req.full_url)
            if req.full_url.endswith("/releases/tags/newsletter-006-newsreel-1"):
                self.assertTrue(req.get_header("Authorization", "").startswith("Bearer "))
                self.assertNotIn("super-secret-token-value", req.full_url)
                return Body(b'{"assets":[{"name":"nordic-crypto-6-newsreel.mp4","url":"https://api.github.com/repos/o/r/releases/assets/9"}]}')
            if req.full_url.endswith("/releases/assets/9"):
                return Body(b"from-api")
            raise AssertionError(req.full_url)

        dest = self.state("video-api.bin")
        url = "https://github.com/nordic-crypto-org/nordic-crypto/releases/download/newsletter-006-newsreel-1/nordic-crypto-6-newsreel.mp4"
        xn.download_url(url, dest, token="super-secret-token-value", attempts=2, sleep=lambda s: None, opener=opener)
        self.assertEqual(open(dest, "rb").read(), b"from-api")
        self.assertTrue(all("github.com/nordic-crypto-org" not in u or "api.github.com" in u for u in calls))


if __name__ == "__main__":
    unittest.main()
