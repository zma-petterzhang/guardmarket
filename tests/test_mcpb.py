import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_mcpb", ROOT/"scripts/build_mcpb.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class CatalogFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/api/v1/status":
            value = {"mode":"test", "currency":"CNY"}
        elif self.path == "/api/v1/skills":
            value = {"skills":[{"id":"platform.text.upper@1.0.0", "name":"text.upper", "price_micros":10000}], "categories":["text"]}
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(value).encode())


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.output = cls.directory/"client.mcpb"
        cls.result = builder.build(cls.output)
        cls.unpacked = cls.directory/"unpacked"
        with zipfile.ZipFile(cls.output) as archive:
            archive.extractall(cls.unpacked)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_deterministic_archive_with_matching_sha256(self):
        second = self.directory/"second.mcpb"
        other = builder.build(second)
        self.assertEqual(self.output.read_bytes(), second.read_bytes())
        self.assertEqual(self.result["fileSha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertEqual(self.result["fileSha256"], other["fileSha256"])

    def test_only_allowlisted_portable_files_are_bundled(self):
        with zipfile.ZipFile(self.output) as archive:
            expected = set(builder.FILES) | {"manifest.json", "server.py", "pyproject.toml"}
            self.assertEqual(set(archive.namelist()), expected)
            self.assertEqual(len(archive.namelist()), len(expected))
            for member in archive.infolist():
                self.assertEqual(member.external_attr >> 16, 0o100644)
                self.assertNotIn("..", Path(member.filename).parts)
                self.assertFalse(Path(member.filename).is_absolute())
        config = tomllib.loads((self.unpacked/"pyproject.toml").read_text())
        self.assertEqual(config["project"]["dependencies"], [])
        self.assertFalse(config["tool"]["uv"]["package"])

    def test_manifest_runtime_and_optional_sensitive_key(self):
        manifest = json.loads((self.unpacked/"manifest.json").read_text())
        self.assertEqual(manifest["manifest_version"], "0.4")
        self.assertEqual(manifest["server"]["type"], "uv")
        self.assertTrue((self.unpacked/manifest["server"]["entry_point"]).is_file())
        self.assertEqual(manifest["server"]["mcp_config"]["command"], "uv")
        self.assertEqual(manifest["server"]["mcp_config"]["args"], ["run","--directory","${__dirname}","server.py"])
        self.assertEqual(manifest["compatibility"]["runtimes"]["python"], ">=3.11")
        key = manifest["user_config"]["api_key"]
        self.assertFalse(key["required"])
        self.assertTrue(key["sensitive"])
        self.assertEqual(key["default"], "")

    def run_bundle(self, messages, url, key=""):
        env = {k:v for k,v in os.environ.items() if not k.startswith(("GUARDMARKET_", "PYTHON"))}
        env.update(GUARDMARKET_URL=url, GUARDMARKET_API_KEY=key)
        result = subprocess.run([sys.executable,"server.py"], cwd=self.unpacked, env=env, input="".join(json.dumps(m)+"\n" for m in messages), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode,0, result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_unpacked_bundle_protocol_and_anonymous_live_discovery(self):
        backend = ThreadingHTTPServer(("127.0.0.1",0), CatalogFixture)
        thread = threading.Thread(target=backend.serve_forever, daemon=True)
        thread.start()
        try:
            messages = [
                {"jsonrpc":"2.0", "id":1, "method":"initialize", "params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"bundle-test","version":"1"}}},
                {"jsonrpc":"2.0", "method":"notifications/initialized"},
                {"jsonrpc":"2.0", "id":2, "method":"tools/list"},
                {"jsonrpc":"2.0", "id":3, "method":"tools/call", "params":{"name":"market.search","arguments":{}}},
                {"jsonrpc":"2.0", "id":4, "method":"tools/call", "params":{"name":"market.wallet","arguments":{}}},
            ]
            replies = self.run_bundle(messages, f"http://127.0.0.1:{backend.server_port}")
            self.assertEqual(len(replies[1]["result"]["tools"]),5)
            for tool in replies[1]["result"]["tools"]:
                self.assertIn("destructiveHint", tool["annotations"])
                self.assertIn("idempotentHint", tool["annotations"])
            self.assertTrue(replies[2]["result"]["structuredContent"]["ok"])
            self.assertEqual(replies[2]["result"]["structuredContent"]["skills"][0]["name"],"text.upper")
            self.assertEqual(replies[3]["result"]["structuredContent"]["error"]["code"],"authentication_required")
        finally:
            backend.shutdown()
            backend.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
