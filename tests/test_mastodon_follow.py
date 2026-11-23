#!/usr/bin/env python3
"""tools/mastodon_follow.py: pick and follow Explore accounts within rate limits. No network."""
import os, sys, unittest, urllib.error
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import mastodon_follow as mf


def acct(i, **kw):
    a = {"id": str(i), "acct": f"user{i}", "bot": False, "locked": False}
    a.update(kw)
    return a


class FakeClient:
    def __init__(self, sugg, trend, rel=None, remaining=None, rate_limit_after=None, fail_ids=()):
        self.sugg, self.trend, self.rel = sugg, trend, rel or {}
        self.remaining, self.rate_limit_after, self.fail_ids = remaining, rate_limit_after, set(fail_ids)
        self.follows = []

    def call(self, method, path, params=None):
        if path == "/api/v1/accounts/verify_credentials":
            return {"id": "me"}, {}
        if path == "/api/v2/suggestions":
            return [{"source": "global", "account": a} for a in self.sugg], {}
        if path == "/api/v1/trends/statuses":
            return [{"id": f"s{a['id']}", "account": a} for a in self.trend], {}
        if path == "/api/v1/accounts/relationships":
            return [dict(id=i, **self.rel.get(i, {})) for i in params["id[]"]], {}
        if method == "POST" and path.endswith("/follow"):
            aid = path.split("/")[-2]
            if self.rate_limit_after is not None and len(self.follows) >= self.rate_limit_after:
                raise mf.RateLimited("soon")
            if aid in self.fail_ids:
                raise urllib.error.HTTPError(path, 422, "nope", {}, None)
            self.follows.append(aid)
            hdr = {} if self.remaining is None else {"X-RateLimit-Remaining": str(self.remaining - len(self.follows))}
            return {"id": aid, "following": True}, hdr
        raise AssertionError(path)


def run(client, ledger=None, **kw):
    kw.setdefault("max_follows", 10)
    kw.setdefault("reserve", 50)
    return mf.run(client, set() if ledger is None else ledger, sleep=lambda s: None, **kw)


class Tests(unittest.TestCase):
    def test_caps_at_max_and_merges_suggestions_then_trends(self):
        c = FakeClient([acct(i) for i in range(5)], [acct(i) for i in range(3, 20)])
        self.assertEqual(len(run(c, max_follows=8)), 8)
        self.assertEqual(c.follows, [str(i) for i in range(8)])

    def test_skips_self_bots_locked_groups_moved_and_existing_follows(self):
        sugg = [acct("me"), acct(1, bot=True), acct(2, locked=True), acct(3, group=True),
                acct(4, moved={"id": "x"}), acct(5), acct(6), acct(7), acct(8)]
        rel = {"5": {"following": True}, "6": {"requested": True}, "7": {"blocked_by": True}}
        c = FakeClient(sugg, [], rel=rel)
        run(c)
        self.assertEqual(c.follows, ["8"])

    def test_never_refollows_ledger_ids_and_records_new_ones(self):
        ledger = {"1"}
        c = FakeClient([acct(1), acct(2)], [])
        run(c, ledger)
        self.assertEqual(c.follows, ["2"])
        self.assertEqual(ledger, {"1", "2"})

    def test_stops_on_429(self):
        c = FakeClient([acct(i) for i in range(10)], [], rate_limit_after=3)
        self.assertEqual(len(run(c)), 3)

    def test_stops_at_reserve(self):
        c = FakeClient([acct(i) for i in range(10)], [], remaining=53)
        run(c, reserve=50)
        self.assertEqual(len(c.follows), 3)

    def test_failed_follow_is_skipped_and_not_retried(self):
        ledger = set()
        c = FakeClient([acct(1), acct(2)], [], fail_ids={"1"})
        self.assertEqual(run(c, ledger), ["user2"])
        self.assertIn("1", ledger)

    def test_dry_run_follows_nobody(self):
        ledger = set()
        c = FakeClient([acct(1)], [])
        run(c, ledger, dry_run=True)
        self.assertEqual((c.follows, ledger), ([], set()))

    def test_rejects_out_of_range_max(self):
        with self.assertRaises(SystemExit):
            mf.main(["--max", "43"])


if __name__ == "__main__":
    unittest.main()
