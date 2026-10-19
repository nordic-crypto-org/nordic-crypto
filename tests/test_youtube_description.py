import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import youtube_upload  # noqa: E402


def test_description_links_the_issue_not_the_sources():
    doc = json.loads(youtube_upload.ISSUES.read_text())
    for it in doc["issues"]:
        d = youtube_upload.description(it, "https://nordiccrypto.no/")
        assert f"Read the issue and all sources: https://nordiccrypto.no/newsletter/{it['id']}/" in d
        assert "Sources:" not in d and "…" not in d and "..." not in d
        assert youtube_upload.LOGOS in d and "Not investment advice." in d
        assert len(d) <= youtube_upload.MAX_DESCRIPTION
        hosts = {re.match(r"https?://([^/]+)", u).group(1) for u in re.findall(r"https?://\S+", d)}
        assert hosts <= {"nordiccrypto.no", "t.me", "x.com", "www.facebook.com", "www.instagram.com"}
