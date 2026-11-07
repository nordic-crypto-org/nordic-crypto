#!/usr/bin/env python3
"""Cloudflare failure logs name the missing token permission and never keep the token."""
import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import cf_permission


def run(step, exit_code, text):
    out, err = io.StringIO(), io.StringIO()
    old_out, old_err, old_in = sys.stdout, sys.stderr, sys.stdin
    sys.stdout, sys.stderr, sys.stdin = out, err, io.StringIO(text)
    try:
        code = cf_permission.main(["--step", step, "--exit-code", str(exit_code)])
    finally:
        sys.stdout, sys.stderr, sys.stdin = old_out, old_err, old_in
    return code, out.getvalue(), err.getvalue()


class CfPermission(unittest.TestCase):
    def test_r2_auth_names_the_permission_and_hides_the_token(self):
        token = "cfut_secret_value_should_not_appear"
        text = (
            "A request to the Cloudflare API (/accounts/abc/r2/buckets) failed.\n"
            "Authentication error [code: 10000]\n"
            f"Authorization: Bearer {token}\n"
        )
        result = cf_permission.classify(text, "r2-info", secrets=[token])
        self.assertEqual(result["kind"], "auth")
        self.assertEqual(result["permission"], "Workers R2 Storage Edit")
        self.assertNotIn(token, result["redacted"])
        self.assertIn("[redacted]", result["redacted"])
        self.assertIn("Missing token permission: Workers R2 Storage Edit.", result["message"])

    def test_env_token_is_redacted(self):
        token = "super-secret-token-value"
        os.environ["CLOUDFLARE_API_TOKEN"] = token
        try:
            result = cf_permission.classify(f"failed with {token}", "d1")
        finally:
            os.environ.pop("CLOUDFLARE_API_TOKEN", None)
        self.assertNotIn(token, result["redacted"])
        self.assertIn("[redacted]", result["redacted"])

    def test_missing_bucket_exits_2(self):
        text = (
            "A request to the Cloudflare API (/accounts/abc/r2/buckets/nordic-crypto-story-images) failed.\n"
            "The specified bucket does not exist. [code: 10006]\n"
        )
        self.assertEqual(cf_permission.classify(text, "r2-info")["kind"], "missing")
        code, out, err = run("r2-info", 1, text)
        self.assertEqual(code, 2)
        self.assertNotIn("::error::", err)
        self.assertIn("10006", out)

    def test_bucket_already_exists_is_success(self):
        text = "A bucket with this name already exists. [code: 10004]\n"
        self.assertEqual(cf_permission.classify(text, "r2-create")["kind"], "exists")
        code, _out, err = run("r2-create", 1, text)
        self.assertEqual(code, 0)
        self.assertNotIn("::error::", err)

    def test_d1_auth_names_d1_edit(self):
        text = (
            "A request to the Cloudflare API (/accounts/x/d1/database/y/query) failed.\n"
            "Authentication error [code: 10000]\n"
        )
        result = cf_permission.classify(text, "d1")
        self.assertEqual(result["permission"], "D1 Edit")
        code, _out, err = run("d1", 1, text)
        self.assertEqual(code, 1)
        self.assertIn("::error::Missing token permission: D1 Edit.", err)

    def test_custom_domain_auth_names_routes_and_dns(self):
        text = (
            "A request to the Cloudflare API "
            "(/accounts/x/workers/scripts/nordic-crypto-content/domains/records) failed.\n"
            "Authentication error [code: 10000]\n"
        )
        perm = cf_permission.classify(text, "deploy")["permission"]
        self.assertIn("Workers Routes Edit", perm)
        self.assertIn("DNS Edit", perm)
        self.assertNotIn("Workers Scripts Edit", perm)

    def test_deploy_auth_without_a_path_names_the_deploy_permissions(self):
        perm = cf_permission.classify("Authentication error [code: 10000]\n", "deploy")["permission"]
        self.assertIn("Workers Scripts Edit", perm)
        self.assertIn("Workers Routes Edit", perm)
        self.assertIn("DNS Edit", perm)

    def test_missing_zone_is_not_called_a_token_permission(self):
        text = "Could not find zone for `api.nordiccrypto.no`. Make sure the domain exists in your account.\n"
        result = cf_permission.classify(text, "deploy")
        self.assertEqual(result["kind"], "zone")
        self.assertIsNone(result["permission"])
        self.assertNotIn("Missing token permission", result["message"])
        self.assertIn("nordiccrypto.no", result["message"])
        code, _out, err = run("deploy", 1, text)
        self.assertEqual(code, 1)
        self.assertIn("::error::", err)
        self.assertIn("nordiccrypto.no", err)

    def test_a_successful_command_does_not_raise_an_error(self):
        code, _out, err = run("deploy", 0, "Authentication error [code: 10000]\n")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
