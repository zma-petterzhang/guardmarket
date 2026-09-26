"""MCPB entry point; optional empty host configuration means anonymous mode."""
import os

# MCPB hosts substitute an optional unset field as an empty string. Keep the
# client strict for malformed nonempty credentials, while supporting no key.
if os.environ.get("GUARDMARKET_API_KEY") == "":
    os.environ.pop("GUARDMARKET_API_KEY")

from guardmarket_mcp.client import main

if __name__ == "__main__":
    raise SystemExit(main())
