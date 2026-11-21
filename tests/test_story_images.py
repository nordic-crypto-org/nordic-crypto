#!/usr/bin/env python3
"""Story illustrations: one picture per story, styles that do not repeat, nothing written to git."""
import datetime as dt, io, json, os, random, shutil, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from tools import d1_store, story_images
import x_post_image as painter


NOW = dt.datetime(2026, 11, 6, 12, tzinfo=dt.timezone.utc)


def story(i, day="2026-11-08", **kw):
    row = {"id": i, "status": "published", "published": f"{day}T08:00:00+00:00",
           "title_en": f"Story {i}", "title": f"Sak {i}", "summary": "A Nordic exchange changed a rule.",
           "country": "NO", "topics": ["regulation"], "source_name": "NRK"}
    row.update(kw)
    return row


def png_bytes():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 36), (20, 40, 50)).save(buf, format="PNG")
    return buf.getvalue()


class StoryImages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="nc-simg-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.store = d1_store.open_sqlite(os.path.join(self.tmp, "c.sqlite"))
        story_images.reset_index()
        self.addCleanup(story_images.reset_index)

    def test_private_backup_bucket_is_not_the_story_bucket(self):
        os.environ.pop(story_images.BUCKET_ENV, None)
        os.environ["CF_R2_BUCKET"] = "nordic-crypto-content-backup"
        try:
            self.assertIn(story_images.BUCKET_ENV, story_images.storage_gaps())
            self.assertEqual(story_images.bucket_name(), "")
        finally:
            os.environ.pop("CF_R2_BUCKET", None)

    def test_public_record_has_url_and_not_the_prompt(self):
        rec = story_images.public_record({
            "story_id": "abc123", "style_id": "woodcut-mining", "kind": "ai",
            "width": 1280, "height": 720, "created_at": "2026-11-06T00:00:00Z",
            "prompt": "secret prompt",
        }, "Headline")
        self.assertTrue(rec["url"].startswith("https://api.nordiccrypto.no/story-images/abc123.png?v="))
        self.assertEqual(rec["kind"], "original")
        self.assertNotIn("prompt", rec)
        self.assertEqual(rec["alt"], "Headline")

    def test_one_image_then_skip_and_style_does_not_repeat(self):
        stored = []

        def generator(prompt):
            self.assertNotIn("tintin", prompt.lower())
            self.assertNotIn("nrk", prompt.lower())
            return png_bytes()

        def uploader(path, key):
            stored.append(key)
            self.assertTrue(os.path.isfile(path))

        items = [story("aaaa11111111", topics=["mining"], title_en="Tintin and a data hall"),
                 story("bbbb22222222", day="2026-11-09")]
        first = story_images.generate_missing(
            items, self.store, now=NOW, generator=generator, uploader=uploader, rng=random.Random(1))
        self.assertEqual(first["generated"], 2)
        self.assertEqual(len(stored), 2)
        styles = [r["style_id"] for r in self.store.query("SELECT style_id FROM story_images ORDER BY story_id")]
        self.assertEqual(len(set(styles)), 2)
        prompts = self.store.query("SELECT prompt FROM story_images")
        self.assertTrue(all("tintin" not in (p["prompt"] or "").lower() for p in prompts))
        again = story_images.generate_missing(
            items, self.store, now=NOW, generator=generator, uploader=uploader, rng=random.Random(1))
        self.assertEqual(again["generated"], 0)
        self.assertEqual(again["skipped"], 2)
        self.assertEqual(len(stored), 2)

    def test_library_grows_when_every_style_was_used_recently(self):
        ids = [r["id"] for r in self.store.query("SELECT id FROM story_image_styles")]
        self.assertGreaterEqual(len(ids), 11)
        self.store.execute("UPDATE story_image_style_state SET recent = ? WHERE id = 1", (json.dumps(ids),))
        stored = []
        story_images.generate_missing(
            [story("cccc33333333", topics=["mining"])], self.store, now=NOW,
            generator=lambda prompt: png_bytes(), uploader=lambda path, key: stored.append(key),
            rng=random.Random(2))
        grown = self.store.query("SELECT id, origin, prompt FROM story_image_styles WHERE origin = 'topic'")
        self.assertEqual(len(grown), 1)
        self.assertNotIn(grown[0]["id"], ids)
        self.assertIn("original", grown[0]["prompt"].lower())
        row = story_images.image_row(self.store, "cccc33333333")
        self.assertEqual(row["kind"], "ai")
        self.assertEqual(row["style_id"], grown[0]["id"])

    def test_fallback_card_is_replaced_once_when_a_generator_is_available(self):
        story_images.generate_missing(
            [story("dddd44444444")], self.store, now=NOW,
            generator=lambda prompt: None, uploader=lambda path, key: None, rng=random.Random(3))
        self.assertEqual(story_images.image_row(self.store, "dddd44444444")["kind"], "fallback")
        story_images.generate_missing(
            [story("dddd44444444")], self.store, now=NOW,
            generator=lambda prompt: None, uploader=lambda path, key: None, rng=random.Random(3))
        self.assertEqual(story_images.image_row(self.store, "dddd44444444")["kind"], "fallback")
        story_images.generate_missing(
            [story("dddd44444444")], self.store, now=NOW,
            generator=lambda prompt: png_bytes(), uploader=lambda path, key: None, rng=random.Random(3))
        self.assertEqual(story_images.image_row(self.store, "dddd44444444")["kind"], "ai")

    def test_old_and_pending_stories_are_not_generated(self):
        items = [story("eeee55555555", day="2026-10-01"),
                 story("ffff66666666", status="pending")]
        counts = story_images.generate_missing(
            items, self.store, now=NOW, generator=lambda p: png_bytes(),
            uploader=lambda path, key: None, rng=random.Random(4))
        self.assertEqual(counts["considered"], 0)
        self.assertIsNone(story_images.image_row(self.store, "eeee55555555"))

    def test_stories_before_the_cutoff_are_not_backfilled(self):
        # 6 Nov is inside the old 7-day window. The cutoff is 7 Nov 2026 08:16 UTC.
        items = [
            story("aa11aa11aa11", day="2026-11-06"),
            story("bb22bb22bb22", published="2026-11-07T08:16:00Z"),
            story("cc33cc33cc33", published="2026-11-07T08:16:01Z"),
            story("dd44dd44dd44", status="pending", published="2026-11-08T12:00:00Z"),
        ]
        counts = story_images.generate_missing(
            items, self.store, now=NOW, published_after="2020-01-01T00:00:00Z",
            generator=lambda p: png_bytes(), uploader=lambda path, key: None, rng=random.Random(4))
        self.assertEqual(counts["considered"], 1)
        self.assertEqual(counts["generated"], 1)
        self.assertIsNone(story_images.image_row(self.store, "aa11aa11aa11"))
        self.assertIsNone(story_images.image_row(self.store, "bb22bb22bb22"))
        self.assertEqual(story_images.image_row(self.store, "cc33cc33cc33")["kind"], "ai")
        self.assertIsNone(story_images.image_row(self.store, "dd44dd44dd44"))

    def test_days_flag_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            story_images.main(["generate", "--days", "7"])
        self.assertEqual(caught.exception.code, 2)

    def test_a_cutoff_that_is_not_a_time_is_refused(self):
        self.assertEqual(story_images.main(["generate", "--published-after", "not-a-time"]), 2)

    def test_issue_image_is_a_new_style_in_r2_not_git(self):
        from PIL import Image
        meta = {
            "id": "006", "title": "Nordic Crypto #6: NRK says banks moved",
            "subtitle": "The week",
            "stories_list": [{"title": "E24 on a licence"}, {"title": "A quiet market"}],
        }
        stored = {}

        def uploader(path, key):
            stored["key"] = key
            self.assertTrue(os.path.realpath(path).startswith(os.path.realpath(tempfile.gettempdir()) + os.sep))
            self.assertFalse(os.path.realpath(path).startswith(os.path.realpath(ROOT) + os.sep))

        info = story_images.generate_issue_image(
            meta, self.store, now=NOW, generator=lambda prompt: png_bytes(), uploader=uploader)
        self.addCleanup(lambda: os.path.exists(info["path"]) and os.unlink(info["path"]))
        self.assertEqual(info["kind"], "ai")
        self.assertEqual(info["story_id"], "newsletter-006")
        self.assertEqual(stored["key"], "story-images/newsletter-006.png")
        self.assertTrue(info["style_id"].startswith(("cyanotype-", "wax-resist-", "copperplate-", "marbled-paper-")))
        self.assertNotIn(info["style_id"], painter.STYLE_IDS)
        im = Image.open(info["path"])
        self.assertEqual(im.size, (1280, 720))
        self.assertEqual(im.getpixel((1240, 40))[:3], painter.TEAL)
        prompt = self.store.query("SELECT prompt FROM story_images WHERE story_id = ?", ("newsletter-006",))[0]["prompt"]
        self.assertNotRegex(prompt, r"(?i)\b(nrk|e24)\b")
        self.assertIn("no logos", prompt.lower())
        again = story_images.generate_issue_image(
            meta, self.store, now=NOW, generator=lambda prompt: (_ for _ in ()).throw(AssertionError("reuse")),
            uploader=lambda *a: self.fail("reuse must not upload"))
        self.assertTrue(again["reused"])
        self.assertEqual(again["style_id"], info["style_id"])
        self.assertIsNone(again["path"])

    def test_issue_image_is_not_stored_when_the_model_returns_nothing(self):
        meta = {"id": "006", "title": "Nordic Crypto #6: A quiet week", "subtitle": "News", "stories_list": []}
        with self.assertRaises(RuntimeError):
            story_images.generate_issue_image(
                meta, self.store, now=NOW, generator=lambda prompt: None,
                uploader=lambda *a: self.fail("fallback must not be stored"))
        self.assertIsNone(story_images.image_row(self.store, "newsletter-006"))

    def test_workflows_pass_the_cutoff_and_not_a_day_window(self):
        for rel in (".github/workflows/deploy.yml", ".github/workflows/d1-publish.yml",
                    ".github/workflows/story-images.yml"):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("2026-11-07T08:16:00Z", text, rel)
            self.assertNotIn("--days", text, rel)
            self.assertIn("--published-after", text, rel)
        with open(os.path.join(ROOT, ".github/workflows/story-images-setup.yml"), encoding="utf-8") as fh:
            setup = fh.read()
        self.assertIn("workflow_dispatch:", setup)
        self.assertNotIn("schedule:", setup)
        self.assertNotIn("set -x", setup)
        self.assertNotIn("echo \"$CLOUDFLARE_API_TOKEN\"", setup)
        self.assertNotIn("echo ${{ secrets", setup)
        self.assertIn("nordic-crypto-story-images", setup)
        self.assertIn("d1 migrations apply nordic-crypto-content --remote", setup)
        self.assertIn("wrangler deploy", setup)
        self.assertIn("Workers R2 Storage Edit", setup)

    def test_page_uses_the_url_and_falls_back_without_one(self):
        import build
        build.LANG = "en"
        url = "https://api.nordiccrypto.no/story-images/abc123.png?v=2026-11-06T00%3A00%3A00Z"
        item = {"id": "abc123", "story_image": {"url": url, "width": 1280, "height": 720, "alt": "Headline", "kind": "original"}}
        html = build.story_hero(item, "Headline")
        self.assertIn("story-hero", html)
        self.assertIn(url, html)
        self.assertIn("Nordic Crypto", html)
        og = build.story_og_meta(item, "Headline", "Summary")
        self.assertEqual(og["image"], url)
        self.assertEqual(og["image_width"], "1280")
        self.assertEqual(og["image_height"], "720")
        self.assertIsNone(build.story_og_meta({"id": "none"}, "T", "D"))
        self.assertEqual(build.story_hero({"id": "none"}, "T"), "")
        og_plain, image = build.story_share({"id": "none", "summary": "D"}, "T", "D")
        self.assertEqual(image, "https://nordiccrypto.no/assets/brand/og-image.png")
        self.assertEqual(og_plain["image"], image)
        self.assertNotIn("story-images", image)
        self.assertNotIn("/stories/", image)


class StyleChoice(unittest.TestCase):
    def test_never_repeats_a_recent_style(self):
        styles = [{"id": f"s{i}", "prompt": f"style {i}", "origin": "base"} for i in range(11)]
        recent = []
        rng = random.Random(5)
        seen = []
        item = {"topics": ["bitcoin"], "title_en": "A plain coin on a table", "summary": "Markets moved."}
        for _ in range(16):
            choice = painter.choose_style(styles, recent, item, rng)
            self.assertNotIn(choice["id"], set(recent[-painter.RECENT_LIMIT:]))
            if choice["id"] not in {s["id"] for s in styles}:
                styles.append(choice)
                self.assertEqual(choice["origin"], "topic")
            recent = painter.remember_style(recent, choice["id"])
            seen.append(choice["id"])
        self.assertEqual(len(seen), len(set(seen)))
        self.assertGreater(len(styles), 11)

    def test_ligne_claire_prompt_keeps_original_characters_only(self):
        prompt = painter.story_prompt(
            {"title_en": "Tintin and Snowy at NRK", "summary": "Haddock said nothing.", "source_name": "NRK"},
            {"id": "ligne-claire", "prompt": "ligne claire, original adult characters only"},
        )
        low = prompt.lower()
        self.assertNotIn("tintin", low)
        self.assertNotIn("snowy", low)
        self.assertNotIn("haddock", low)
        self.assertNotIn("nrk", low)
        self.assertIn("original", low)


class NewsreelStill(unittest.TestCase):
    def test_downloads_the_stored_url_once(self):
        import newsreel_still
        cache = tempfile.mkdtemp(prefix="nc-still-")
        self.addCleanup(shutil.rmtree, cache, True)
        calls = []

        def read(url):
            calls.append(url)
            if url.endswith(".json"):
                return json.dumps({"id": "abc123", "image": {"url": "https://api.nordiccrypto.no/story-images/abc123.png"}}).encode()
            return png_bytes()

        path = newsreel_still.cached_path("abc123", cache, read=read)
        self.assertTrue(path and os.path.isfile(path))
        again = newsreel_still.cached_path("abc123", cache, read=read)
        self.assertEqual(path, again)
        self.assertEqual(len(calls), 2)
        self.assertIsNone(newsreel_still.cached_path("missing", cache, read=lambda url: b"{}"))


if __name__ == "__main__":
    unittest.main()
