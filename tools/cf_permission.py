#!/usr/bin/env python3
"""Name the Cloudflare token permission a wrangler failure is asking for.

Reads the command's combined output on stdin. Prints that output with any
secret removed, and, on failure, a GitHub Actions error that names the
missing permission. Does not call Cloudflare and does not print the token.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Dashboard names, the ones an operator grants on the API token.
R2_EDIT = "Workers R2 Storage Edit"
D1_EDIT = "D1 Edit"
SCRIPTS_EDIT = "Workers Scripts Edit"
DOMAIN_EDIT = "Workers Routes Edit and DNS Edit"

_AUTH = re.compile(
    r"authentication error|\[code:\s*10000\]|\bcode:\s*10000\b|"
    r"not authorized|unauthorized|insufficient permission|authentication failed",
    re.IGNORECASE,
)
_MISSING = re.compile(
    r"does not exist|doesn't exist|\[code:\s*10006\]|\bcode:\s*10006\b|nosuchbucket",
    re.IGNORECASE,
)
_EXISTS = re.compile(
    r"already exists|already in use|\[code:\s*10004\]|\bcode:\s*10004\b",
    re.IGNORECASE,
)
_ZONE = re.compile(
    r"could not find (a )?zone|make sure the domain exists in your account|"
    r"make sure the domain or its parent zone exists",
    re.IGNORECASE,
)

_STEP_PERMISSION = {
    "r2": R2_EDIT,
    "r2-info": R2_EDIT,
    "r2-create": R2_EDIT,
    "d1": D1_EDIT,
    "deploy": f"{SCRIPTS_EDIT}, {DOMAIN_EDIT}",
}


def secret_values(extra=()):
    found = []
    for value in list(extra):
        if value and len(value) >= 8:
            found.append(value)
    for name in ("CLOUDFLARE_API_TOKEN", "CF_AI_TOKEN", "NC_PRIVATE_TERMS_JSON"):
        value = os.environ.get(name) or ""
        if len(value) >= 8 and value not in found:
            found.append(value)
    return found


def redact(text, extra=()):
    out = text or ""
    for value in secret_values(extra):
        out = out.replace(value, "[redacted]")
    return out


def permission_for(text, step):
    low = (text or "").lower()
    if "/r2/" in low or "r2/buckets" in low or "r2 bucket" in low:
        return R2_EDIT
    if "/d1/" in low:
        return D1_EDIT
    if "/domains" in low or "custom domain" in low or "dns record" in low or "/dns_records" in low:
        return DOMAIN_EDIT
    if "/workers/scripts" in low or "/workers/services" in low:
        return SCRIPTS_EDIT
    return _STEP_PERMISSION.get(step, SCRIPTS_EDIT)


def classify(text, step, secrets=()):
    """kind is auth, zone, missing, exists, or other. The token is not in redacted."""
    redacted = redact(text, secrets)
    if _AUTH.search(redacted):
        perm = permission_for(redacted, step)
        return {
            "kind": "auth",
            "permission": perm,
            "redacted": redacted,
            "message": f"Missing token permission: {perm}.",
        }
    if _ZONE.search(redacted):
        return {
            "kind": "zone",
            "permission": None,
            "redacted": redacted,
            "message": (
                "The zone nordiccrypto.no is not on this Cloudflare account, so "
                "api.nordiccrypto.no was not attached. The hostname stays unresolved "
                "until that zone is on the same account and this workflow is run again. "
                "Do not add a CNAME for api by hand."
            ),
        }
    if _EXISTS.search(redacted):
        return {"kind": "exists", "permission": None, "redacted": redacted, "message": ""}
    if _MISSING.search(redacted):
        return {"kind": "missing", "permission": None, "redacted": redacted, "message": ""}
    return {"kind": "other", "permission": None, "redacted": redacted, "message": f"{step} failed."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--step", required=True)
    ap.add_argument("--exit-code", type=int, required=True)
    args = ap.parse_args(argv)
    result = classify(sys.stdin.read(), args.step)
    if result["redacted"]:
        sys.stdout.write(result["redacted"])
        if not result["redacted"].endswith("\n"):
            sys.stdout.write("\n")
    if args.exit_code == 0:
        return 0
    if result["kind"] == "exists" and args.step == "r2-create":
        return 0
    if result["kind"] == "missing" and args.step == "r2-info":
        return 2
    message = result["message"] or f"{args.step} failed."
    print(f"::error::{message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as err:
        print(f"::error::cf_permission failed: {type(err).__name__}", file=sys.stderr)
        sys.exit(1)
