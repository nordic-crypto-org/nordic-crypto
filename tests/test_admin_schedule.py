import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import admin_schedule


class AdminSchedule(unittest.TestCase):
    def test_workflow_times_come_from_the_yml(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "a.yml"), "w").write('on:\n  schedule:\n    - cron: "45 6 * * 1"\n    - cron: \'0 12 * * *\'\n')
            p = admin_schedule.payload({"schedule": [{"id": "r"}], "workflows": {"a.yml": {"channel": "X", "what": "w", "status": "active"}}}, d)
        self.assertEqual([r["id"] for r in p["schedule"]], ["r", "wf:a.yml:0", "wf:a.yml:1"])
        self.assertEqual(p["schedule"][1], {"channel": "X", "what": "w", "status": "active", "id": "wf:a.yml:0", "cron": "45 6 * * 1",
                                            "tz": "UTC", "source": "workflow:a.yml"})
        self.assertEqual(p["campaigns"], [])

    def test_real_workflow_has_a_cron(self):
        self.assertTrue(admin_schedule.workflow_crons("x-newsletter.yml"))

    def test_post_needs_config(self):
        self.assertIsNone(admin_schedule.post({}, {"NEWSLETTER_WORKER_ORIGIN": "https://w.test", "ADMIN_DELIVERY_TOKEN": "short"}))


if __name__ == "__main__":
    unittest.main()
