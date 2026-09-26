#!/usr/bin/env python3
"""Verify a public GitHub MCPB release and prepare MCP Registry metadata.

This script only reads public release/registry data and writes a local JSON file.
It never authenticates to, or publishes in, the MCP Registry.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = "zma-petterzhang/guardmarket"
REPO_URL = "https://github.com/" + REPOSITORY
SERVER_NAME = "io.github.zma-petterzhang/guardmarket"
SCHEMA = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
MAX_DOWNLOAD = 8 * 1024 * 1024


class PublicReleaseRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if (parsed.scheme != "https" or parsed.hostname not in {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
                or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443)):
            raise ValueError("Release download redirected outside GitHub HTTPS asset hosts")
        return super().redirect_request(request, fp, code, message, headers, newurl)


def read_bytes(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "github.com", "registry.modelcontextprotocol.io"}:
        raise ValueError("Unsupported public metadata host")
    request = urllib.request.Request(url, headers={"Accept": "application/json, application/octet-stream", "User-Agent": "GuardMarket-Registry-Preflight/0.3"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicReleaseRedirect())
    with opener.open(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError("Public artifact did not return HTTP 200")
        raw = response.read(MAX_DOWNLOAD + 1)
    if len(raw) > MAX_DOWNLOAD:
        raise ValueError("Public artifact exceeds the size limit")
    return raw


def read_json(url):
    value = json.loads(read_bytes(url))
    if type(value) is not dict:
        raise ValueError("Public metadata must be an object")
    return value


def valid_version(version):
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        raise ValueError("Expected a final semantic version such as 0.3.0")
    return version


def inspect_bundle(raw, version):
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        infos = bundle.infolist()
        names = [entry.filename for entry in infos]
        if len(names) != len(set(names)) or sum(entry.file_size for entry in infos) > MAX_DOWNLOAD:
            raise ValueError("Duplicate or oversized MCPB contents")
        for entry in infos:
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in entry.filename or
                    stat.S_ISLNK(entry.external_attr >> 16) or
                    any(part in {".git", ".venv", ".market-state", "executor-secrets"} for part in path.parts) or
                    path.suffix in {".key", ".pem", ".db", ".sqlite", ".sqlite3"} or
                    path.name in {".env", "admin-login.json", "billing.py", "store.py", "service.py", "builtins.py"}):
                raise ValueError("MCPB contains a private or unsafe path")
        if "manifest.json" not in names or bundle.getinfo("manifest.json").file_size > 65536:
            raise ValueError("Missing or oversized MCPB manifest")
        manifest = json.loads(bundle.read("manifest.json"))
        if type(manifest) is not dict or manifest.get("version") != version or manifest.get("name") not in {"guardmarket", "guardmarket-mcp"}:
            raise ValueError("MCPB identity/version does not match the release")
        server = manifest.get("server", {})
        if type(server) is not dict or server.get("type") not in {"uv", "python"} or server.get("entry_point") not in names:
            raise ValueError("MCPB lacks its declared Python entry point")


def prepare(version, json_fetch=read_json, bytes_fetch=read_bytes):
    valid_version(version)
    repository = json_fetch("https://api.github.com/repos/" + REPOSITORY)
    if repository.get("private") is not False or repository.get("html_url") != REPO_URL:
        raise ValueError("The exact integration repository must be public")
    release = json_fetch("https://api.github.com/repos/" + REPOSITORY + "/releases/tags/v" + version)
    if release.get("tag_name") != "v" + version or release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("A public final GitHub release with the exact version is required")
    filename = "guardmarket-mcp-" + version + ".mcpb"
    url = REPO_URL + "/releases/download/v" + version + "/" + filename
    assets = release.get("assets", [])
    matches = [asset for asset in assets if asset.get("name") == filename and asset.get("browser_download_url") == url]
    checksums_url = REPO_URL + "/releases/download/v" + version + "/SHA256SUMS"
    checksums_assets = [asset for asset in assets if asset.get("name") == "SHA256SUMS" and asset.get("browser_download_url") == checksums_url]
    if len(matches) != 1 or len(checksums_assets) != 1:
        raise ValueError("Release must contain the exact MCPB and SHA256SUMS assets")
    raw = bytes_fetch(url)
    digest = hashlib.sha256(raw).hexdigest()
    remote_digest = matches[0].get("digest")
    if remote_digest is not None and remote_digest != "sha256:" + digest:
        raise ValueError("MCPB content does not match GitHub's asset digest")
    checksums = bytes_fetch(checksums_url).decode("utf-8")
    matching_lines = [line for line in checksums.splitlines() if re.fullmatch(re.escape(digest) + r"  \*?" + re.escape(filename), line)]
    if len(matching_lines) != 1:
        raise ValueError("MCPB content does not match its released SHA256SUMS entry")
    inspect_bundle(raw, version)
    return {
        "$schema": SCHEMA, "name": SERVER_NAME, "title": "GuardMarket", "version": version,
        "description": "MCP client for commerce/data skills; requires a configured GuardMarket backend.",
        "repository": {"url": REPO_URL, "source": "github"},
        "packages": [{"registryType": "mcpb", "identifier": url, "fileSha256": digest,
                      "transport": {"type": "stdio"}}],
    }


def verify_published(metadata, fetch=read_json):
    if metadata.get("name") != SERVER_NAME:
        raise ValueError("Wrong Registry namespace")
    version = valid_version(metadata.get("version", ""))
    url = "https://registry.modelcontextprotocol.io/v0.1/servers?" + urllib.parse.urlencode({"search": SERVER_NAME})
    response = fetch(url)
    matches = [entry.get("server", {}) for entry in response.get("servers", [])
               if entry.get("server", {}).get("name") == SERVER_NAME and entry.get("server", {}).get("version") == version]
    if not any(entry.get("packages") == metadata["packages"] for entry in matches):
        raise ValueError("Official Registry has not returned this exact name, version and artifact hash")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version")
    parser.add_argument("--output", type=Path, default=Path("server.json"))
    parser.add_argument("--verify-published", type=Path, help="Check an already generated metadata file against the official Registry")
    args = parser.parse_args(argv)
    try:
        if args.verify_published:
            metadata = json.loads(args.verify_published.read_text())
            verify_published(metadata)
            print("Official MCP Registry verified:", metadata["name"], metadata["version"])
        else:
            if not args.version:
                raise ValueError("--version is required")
            metadata = prepare(args.version)
            with args.output.open("x", encoding="utf-8") as output:
                json.dump(metadata, output, ensure_ascii=False, indent=2)
                output.write("\n")
            print("Public release verified; metadata written to", args.output)
            print("No Registry publication was performed by this script.")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
