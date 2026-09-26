#!/usr/bin/env python3
"""Build a deterministic MCPB 0.4 bundle from an explicit public-file allowlist.

The host's uv runtime supplies Python 3.11+. No Python environment, account data,
backend, executor, or third-party dependency is included in this archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "guardmarket_mcp/__init__.py",
    "guardmarket_mcp/__main__.py",
    "guardmarket_mcp/client.py",
    "guardmarket_mcp/validation.py",
    "LICENSE",
    "README.md",
    "SECURITY.md",
)


def read_public(path):
    source = ROOT / path
    if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Expected an ordinary public source file: " + path)
    return source.read_bytes()


def build(output=None):
    project = tomllib.loads(read_public("pyproject.toml").decode())["project"]
    version = project["version"]
    manifest = json.loads(read_public("mcpb/manifest.json"))
    if manifest["version"] != version or manifest["manifest_version"] != "0.4":
        raise ValueError("Bundle and project versions must match")
    if manifest["server"]["type"] != "uv" or manifest["server"]["entry_point"] != "server.py":
        raise ValueError("Expected the reviewed uv entry point")
    output = Path(output) if output else ROOT / "dist" / f"guardmarket-mcp-{version}.mcpb"
    output.parent.mkdir(parents=True, exist_ok=True)
    files = {name:read_public(name) for name in FILES}
    files["manifest.json"] = (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()
    files["server.py"] = read_public("mcpb/server.py")
    files["pyproject.toml"] = (f'[project]\nname = "guardmarket-mcp-bundle"\nversion = "{version}"\nrequires-python = ">=3.11"\ndependencies = []\n\n[tool.uv]\npackage = false\n').encode()
    if sum(map(len, files.values())) > 1_000_000:
        raise ValueError("Unexpected public bundle size")
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content, compresslevel=9)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {"path":str(output), "fileSha256":digest, "size":output.stat().st_size, "members":len(files)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Output .mcpb path; defaults to dist/guardmarket-mcp-VERSION.mcpb")
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False))
