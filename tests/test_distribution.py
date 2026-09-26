from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tomllib
import unittest
from urllib.parse import urlsplit

from guardmarket_mcp import __version__
from guardmarket_mcp.validation import validate_arguments

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key,value in attrs:
            if key in ("href", "src"):
                self.targets.append(value)


class DistributionTests(unittest.TestCase):
    def test_all_catalog_examples_match_schemas(self):
        catalog = json.loads((ROOT/"catalog/skills.json").read_text())
        skills = catalog["skills"]
        self.assertEqual(len(skills), 125)
        self.assertEqual(len({s["name"] for s in skills}), 125)
        for skill in skills:
            with self.subTest(skill=skill["name"]):
                validate_arguments(skill["example_input"], skill["input_schema"])
                validate_arguments(skill["example_output"], skill["output_schema"], max_bytes=131072)
                self.assertEqual(skill["effects"], "pure")
                self.assertTrue((ROOT/"docs/skills"/(skill["name"]+".html")).is_file())

    def test_all_static_internal_links_have_targets(self):
        pages = list((ROOT/"docs").rglob("*.html"))
        self.assertEqual(len(pages), 130)
        for page in pages:
            parser = Links()
            parser.feed(page.read_text())
            for target in parser.targets:
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                with self.subTest(page=page.name, target=target):
                    self.assertTrue(parsed.path.startswith("/guardmarket/"))
                    local = ROOT/"docs"/parsed.path.removeprefix("/guardmarket/")
                    self.assertTrue(local.is_file() or (local/"index.html").is_file())

    def test_package_versions_and_markers(self):
        config = tomllib.loads((ROOT/"pyproject.toml").read_text())
        self.assertEqual(config["project"]["version"], __version__)
        self.assertEqual(config["project"]["dependencies"], [])
        for path in ("plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
            manifest = json.loads((ROOT/path).read_text())
            self.assertEqual(manifest["name"], "guardmarket")
            self.assertEqual(manifest["version"], __version__)
        self.assertIn("<!-- mcp-name: io.github.zma-petterzhang/guardmarket -->", (ROOT/"README.md").read_text())

    def test_distribution_has_no_backend_implementation(self):
        files = {p.name for p in (ROOT/"guardmarket_mcp").glob("*.py")}
        self.assertEqual(files, {"__init__.py", "__main__.py", "client.py", "validation.py"})
        for path in (ROOT/"guardmarket_mcp").glob("*.py"):
            text = path.read_text()
            self.assertNotIn("import sqlite3", text)
            self.assertNotIn("from .builtins", text)

    def test_manifests_and_examples_parse_without_credentials(self):
        for path in [ROOT/"mcp.json", ROOT/".mcp.json", *list((ROOT/"examples").glob("*.json"))]:
            config = json.loads(path.read_text())
            self.assertTrue(config["mcpServers"])
            for server in config["mcpServers"].values():
                self.assertNotIn("Authorization", server.get("headers", {}))
                self.assertNotIn("GUARDMARKET_API_KEY", server.get("env", {}))
        for path in (ROOT/"docs").rglob("*.html"):
            text = path.read_text()
            self.assertNotRegex(text, r"(?:/Users/|owner@guardmarket|mingan-provider@)")


if __name__ == "__main__":
    unittest.main()
