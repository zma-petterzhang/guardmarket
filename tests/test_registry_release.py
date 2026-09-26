"""Release publication refuses unrelated/private/mismatched MCPB artifacts."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_mcpb_registry", ROOT / "scripts/prepare_mcpb_registry.py")
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)


def bundle(version="0.3.0", extra=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"name": "guardmarket-mcp", "version": version, "server": {"type": "uv", "entry_point": "server.py"}}))
        archive.writestr("server.py", "# local fixture only\n")
        for name, contents in (extra or {}).items():
            archive.writestr(name, contents)
    return output.getvalue()


class RegistryReleaseTests(unittest.TestCase):
    def setUp(self):
        self.raw = bundle()
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.repo = {"private": False, "html_url": registry.REPO_URL}
        self.url = registry.REPO_URL + "/releases/download/v0.3.0/guardmarket-mcp-0.3.0.mcpb"
        self.release = {"tag_name": "v0.3.0", "draft": False, "prerelease": False, "assets": [
            {"name": "guardmarket-mcp-0.3.0.mcpb", "browser_download_url": self.url, "digest": "sha256:" + self.digest},
            {"name": "SHA256SUMS", "browser_download_url": self.url.rsplit("/", 1)[0] + "/SHA256SUMS"},
        ]}
        self.checksums = (self.digest + "  guardmarket-mcp-0.3.0.mcpb\n").encode()

    def json_fetch(self, url):
        return self.release if "/releases/tags/" in url else self.repo

    def bytes_fetch(self, url):
        return self.checksums if url.endswith("SHA256SUMS") else self.raw

    def test_public_artifact_identity_and_hash_are_bound_in_metadata(self):
        result = registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)
        self.assertEqual(result["name"], registry.SERVER_NAME)
        self.assertEqual(result["packages"][0]["identifier"], self.url)
        self.assertEqual(result["packages"][0]["fileSha256"], self.digest)
        self.assertNotIn("remotes", result)
        self.assertEqual(result["packages"][0]["registryType"], "mcpb")

    def test_private_repo_draft_release_and_cross_repo_asset_are_rejected(self):
        self.repo["private"] = True
        with self.assertRaisesRegex(ValueError, "public"):
            registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)
        self.repo["private"] = False
        self.release["draft"] = True
        with self.assertRaisesRegex(ValueError, "final GitHub release"):
            registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)
        self.release["draft"] = False
        self.release["assets"][0]["browser_download_url"] = "https://github.com/unrelated/package/releases/file.mcpb"
        with self.assertRaisesRegex(ValueError, "exact MCPB"):
            registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)

    def test_github_digest_and_released_checksum_must_match(self):
        self.release["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "GitHub's asset digest"):
            registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)
        self.release["assets"][0]["digest"] = "sha256:" + self.digest
        self.checksums = ("0" * 64 + "  guardmarket-mcp-0.3.0.mcpb\n").encode()
        with self.assertRaisesRegex(ValueError, "SHA256SUMS"):
            registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)

    def test_archive_version_private_paths_and_traversal_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity/version"):
            registry.inspect_bundle(bundle(version="0.2.0"), "0.3.0")
        for name in ("../bad.py", "/abs.py", ".market-state/data.db", "guardmarket/billing.py", "secret.key"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "private or unsafe"):
                registry.inspect_bundle(bundle(extra={name: "fixture"}), "0.3.0")

    def test_bad_version_never_reaches_public_fetch(self):
        for version in ("latest", "v0.3.0", "0.3.0;echo hi", "../0.3.0", "0.3.0-beta"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                registry.prepare(version, lambda url: self.fail("network reached"), self.bytes_fetch)

    def test_registry_readback_checks_exact_name_version_and_hash(self):
        data = registry.prepare("0.3.0", self.json_fetch, self.bytes_fetch)
        registry.verify_published(data, lambda url: {"servers": [{"server": data}]})
        wrong = {**data, "version": "0.2.0"}
        with self.assertRaisesRegex(ValueError, "exact name, version"):
            registry.verify_published(data, lambda url: {"servers": [{"server": wrong}]})
        with self.assertRaisesRegex(ValueError, "exact name, version"):
            registry.verify_published(data, lambda url: {"servers": []})


if __name__ == "__main__":
    unittest.main()
