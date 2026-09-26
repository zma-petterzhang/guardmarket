# GuardMarket — commerce and data skills over MCP

<!-- mcp-name: io.github.zma-petterzhang/guardmarket -->

[中文](README.zh-CN.md) · [125-skill catalog](https://zma-petterzhang.github.io/guardmarket/) · [Releases](https://github.com/zma-petterzhang/guardmarket/releases) · [Integration examples](examples/README.md)

GuardMarket gives MCP clients five tools to discover versioned skills, inspect their schemas and prices, invoke with an explicit spending cap, and read wallet balances and receipts. The catalog describes **125 implemented commerce, inventory, CSV, JSON, text, date, math, statistics, encoding, validation, and unit-conversion skills**.

**This repository is the public client and documentation.** Skill execution, accounts, and billing run in a separately operated GuardMarket backend. Installing this client does not create a backend or a wallet. No public production MCP endpoint, PyPI listing, or official directory approval is claimed. The static website is documentation, not an execution endpoint. The bundled examples are synthetic and contain no account data.

## Install and connect

**Desktop bundle:** download `guardmarket-mcp-0.3.0.mcpb` from [release v0.3.0](https://github.com/zma-petterzhang/guardmarket/releases/tag/v0.3.0) and verify it against `SHA256SUMS`. Open it in a host that supports **MCPB 0.4 and its uv runtime**. The host manages Python 3.11+; the bundle has no external Python dependencies. Configure your actual backend URL in the install form. Leave the masked consumer API key blank for anonymous discovery. Hosts supporting only older MCPB formats should use the wheel/stdio installation below. This bundle still needs a running backend; it does not install the marketplace server. See [bundle details](examples/README.md#desktop-mcpb-bundle).

Python 3.11+ is required. The Python client has no runtime dependencies.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install "git+https://github.com/zma-petterzhang/guardmarket.git@v0.3.0"
.venv/bin/guardmarket-mcp --version
```

For installation without Git, download the wheel from [release v0.3.0](https://github.com/zma-petterzhang/guardmarket/releases/tag/v0.3.0), verify its SHA-256 against the release `SHA256SUMS`, then run `python -m pip install /path/to/guardmarket_mcp-0.3.0-py3-none-any.whl`. Pin a version or commit in production. On Windows use `.venv\Scripts\python.exe` and `.venv\Scripts\guardmarket-mcp.exe`.

Set `GUARDMARKET_URL` to your backend origin, for example `http://127.0.0.1:8787` for a local instance. The client accepts HTTPS origins and numeric-loopback HTTP origins only. Redirects and environment HTTP proxies are disabled.

```sh
export GUARDMARKET_URL=http://127.0.0.1:8787
.venv/bin/guardmarket-mcp
```

The command waits for MCP messages on standard input; it is normally launched by your AI client. `market.search` and `market.describe` work anonymously if the backend permits public discovery. The other three tools require a consumer API key created in that backend's account settings. Provide it via the client's environment (`GUARDMARKET_API_KEY`) or a user-owned mode-0600 regular file (`--key-file /absolute/path/key`). The key-file option is POSIX-only; environment variables work on Windows. Never put a real key in a committed configuration or a chat message.

## Tools and billing behavior

| MCP tool | Purpose | Authorization |
| --- | --- | --- |
| `market.search` | Search current published skills and prices | Anonymous |
| `market.describe` | Read a selected version's schemas, examples, effects, and price | Anonymous |
| `market.invoke` | Run a user-authorized skill with `max_price_micros` and `idempotency_key` | API key |
| `market.wallet` | Read available/reserved balances and currency | API key |
| `market.receipt` | Retrieve an owned invocation result and billing state | API key |

First search, then describe the exact returned `skill_id`, then invoke. One currency unit equals 1,000,000 micros. The documented ¥0.01 example is **a demo price**, not a promise about a deployment. The selected backend reports its currency, test/production mode, and actual prices. Test mode uses simulated funds. Successful invocations are chargeable; a pending or uncertain invocation may retain a hold. After an uncertain result, reuse the same idempotency key and identical arguments. Do not submit a new key to “retry.”

Example use cases: calculate a cart total with supplied tax and discount rates; validate and normalize product data; escape CSV formulas before spreadsheet export; compare inventory reorder thresholds; summarize provided numbers. These tools do not obtain live tax rates, exchange rates, stock prices, or shipping quotes. The original 125 functions transform supplied data; third-party skills may have external effects, disclosed by `market.describe`.

## Connect an AI client

[Examples and verified source references](examples/README.md) cover Claude Desktop, Claude Code, Qwen Code, Qwen-Agent, and Codex. The portable `plugin.json`, `mcp.json`, and `skills/` bundle also includes Codex and Claude compatibility manifests. Install the client first so `guardmarket-mcp` is on the launcher PATH, or use the executable's absolute path.

ChatGPT and Claude web connectors require a deployed public HTTPS MCP endpoint and its configured authorization flow. They cannot connect to a laptop's stdio command through a repository URL. A GitHub repository, documentation website, or `llms.txt` does not automatically install tools in any model or guarantee indexing.

## Development and release

```sh
python -m unittest discover -s tests -v
python scripts/build_docs.py
python -m pip install build
python -m build
python scripts/build_mcpb.py
```

CI validates Python 3.11–3.13, regenerates the static site, and builds the wheel and MCPB. Pushing a `v*` tag creates a GitHub release with a wheel, source archive, desktop MCPB bundle, and SHA-256 checksums; it does not publish to PyPI or any AI vendor directory. The MCPB builder uses an explicit allowlist and deterministic ZIP metadata, and prints its `fileSha256` for registry preparation. GitHub Pages serves `docs/` using its deployment workflow. Public catalog metadata is a versioned snapshot; the chosen backend remains authoritative at invocation time.

A separate manual GitHub Actions workflow prepares and publishes the released MCPB's metadata to the MCP Registry using GitHub OIDC. It verifies the release artifact and its checksum first. A successful registry receipt is required before claiming registration; MCP Registry publication is separate from OpenAI or Claude plugin-directory review.

[Security](SECURITY.md) · [Privacy and data handling](https://zma-petterzhang.github.io/guardmarket/privacy.html) · [Client terms](https://zma-petterzhang.github.io/guardmarket/terms.html)
