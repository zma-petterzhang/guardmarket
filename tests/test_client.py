import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from guardmarket_mcp.client import Client, _json, _key_file, serve, TOOLS


class Backend(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append((self.path, self.headers.get("Authorization")))
        status = 200
        if self.path == "/api/v1/status":
            data = {"mode":"test", "currency":"CNY"}
        elif self.path.startswith("/api/v1/skills"):
            if self.server.redirect:
                self.send_response(302)
                self.send_header("Location", self.server.redirect)
                self.end_headers()
                return
            data = {"skills":[{"id":"platform.text.upper@1.0.0", "name":"text.upper", "price_micros":10000, "internal":"must be omitted"}], "categories":["text"]}
        elif self.path == "/api/v1/wallet":
            data = {"available_micros":1000000, "reserved_micros":0}
        else:
            status, data = 404, {"error":{"code":"not_found"}}
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        self.server.requests.append((self.path, self.headers.get("Authorization")))
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.bodies.append(body)
        data = {"id":"inv_test", "state":"succeeded", "result":{"text":"HELLO"}, "charged_micros":10000}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
        cls.server.daemon_threads = True
        cls.server.requests, cls.server.bodies, cls.server.redirect = [], [], None
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.server.requests.clear()
        self.server.bodies.clear()
        self.server.redirect = None

    def test_anonymous_discovery_sends_no_authorization(self):
        result = Client(self.url).tool("market.search", {"search":"text.upper"})
        self.assertTrue(result["ok"])
        self.assertTrue(result["market"]["test_funds"])
        self.assertNotIn("internal", result["skills"][0])
        self.assertTrue(all(auth is None for _,auth in self.server.requests))

    def test_anonymous_private_tool_blocked_before_network(self):
        result = Client(self.url).tool("market.wallet", {})
        self.assertEqual(result["error"]["code"], "authentication_required")
        self.assertEqual(self.server.requests, [])

    def test_authenticated_invocation_preserves_cap_and_idempotency(self):
        key = "test_only_" + "a" * 40
        args = {"skill_id":"platform.text.upper@1.0.0", "arguments":{"text":"hello"}, "idempotency_key":"invoice-demo-123", "max_price_micros":10000}
        result = Client(self.url, key).tool("market.invoke", args)
        self.assertTrue(result["ok"])
        self.assertEqual(self.server.bodies, [args])
        self.assertEqual(self.server.requests[-1], ("/api/v1/invocations", "Bearer " + key))

    def test_missing_price_cap_blocked(self):
        result = Client(self.url, "a" * 40).tool("market.invoke", {"skill_id":"text.upper", "arguments":{}, "idempotency_key":"call-12345"})
        self.assertFalse(result["ok"])
        self.assertEqual(self.server.requests, [])

    def test_redirect_not_followed(self):
        self.server.redirect = self.url + "/credential-leak"
        result = Client(self.url, "b" * 40).tool("market.search", {})
        self.assertEqual(result["error"]["code"], "gateway_redirect_rejected")
        self.assertEqual([p for p,_ in self.server.requests], ["/api/v1/status", "/api/v1/skills"])

    def test_fixed_origin_and_key_validation(self):
        for url in ["http://example.com", "http://localhost:8787", "ftp://example.com", "https://user:pass@example.com", "https://example.com/api", "https://example.com?x=1", "https://example.com#secret", "https://example.com\n"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                Client(url)
        for key in ["", "short", "x"*32+"\n", "x"*257]:
            with self.subTest(key_length=len(key)), self.assertRaises(ValueError):
                Client(self.url, key)

    def test_inherited_proxy_is_not_used(self):
        with patch.dict(os.environ, {"http_proxy":"http://127.0.0.1:1", "HTTP_PROXY":"http://127.0.0.1:1", "NO_PROXY":"", "no_proxy":""}):
            self.assertTrue(Client(self.url).tool("market.search", {})["ok"])

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW") and hasattr(os, "getuid"), "POSIX secure key file")
    def test_key_file_permissions_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"key"
            path.write_text("x"*40)
            path.chmod(0o600)
            self.assertEqual(_key_file(path), "x"*40)
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                _key_file(path)
            path.chmod(0o600)
            link = Path(tmp)/"link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                _key_file(link)

    def test_malformed_json_rejected(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}', b'"\xff"']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                _json(raw)

    def test_unknown_or_extra_tool_arguments_never_reach_network(self):
        client = Client(self.url)
        for name,args in [("market.nope", {}), ("market.search", {"search":"x", "leak":"no"}), ("market.describe", {"skill_id":"../../etc/passwd"})]:
            self.assertFalse(client.tool(name,args)["ok"])
        self.assertEqual(self.server.requests, [])

    def test_stdio_protocol_and_tool_list_without_backend_access(self):
        messages = [
            {"jsonrpc":"2.0", "id":1, "method":"initialize", "params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}},
            {"jsonrpc":"2.0", "method":"notifications/initialized"},
            {"jsonrpc":"2.0", "id":2, "method":"tools/list"},
            {"jsonrpc":"2.0", "id":3, "method":"tools/call", "params":{"name":"market.search","arguments":{}}},
        ]
        inp = io.BytesIO(('\n'.join(json.dumps(v) for v in messages)+'\n').encode())
        out = io.StringIO()
        serve(Client(self.url), inp, out)
        replies = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(len(replies), 3)
        self.assertEqual(replies[0]["result"]["serverInfo"]["version"], "0.3.0")
        self.assertEqual(len(replies[1]["result"]["tools"]), 5)
        self.assertTrue(replies[2]["result"]["structuredContent"]["ok"])

    def test_stdio_requires_initialization(self):
        out = io.StringIO()
        serve(Client(self.url), io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'), out)
        self.assertEqual(json.loads(out.getvalue())["error"]["code"], -32000)


if __name__ == "__main__":
    unittest.main()
