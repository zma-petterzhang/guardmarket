# Client setup / 客户端接入

Install the versioned public client first, then configure an existing GuardMarket backend. Replace executable paths and the loopback development URL with real values. Do not use the documentation site as `GUARDMARKET_URL`; it cannot execute skills. Anonymous discovery needs no key. Authenticated calls use a consumer key in the launcher environment or an owned POSIX mode-0600 key file. GUI applications may not inherit terminal environment variables.

The configurations below use stdio MCP. They have been checked against the official configuration formats; this repository's automated tests verify the MCP protocol. End-to-end testing of each vendor's authenticated desktop/web application is a separate operator step, not claimed here.

## Desktop MCPB bundle

The release's `guardmarket-mcp-0.3.0.mcpb` is a ZIP-format MCP bundle using manifest version **0.4**, `server.type = "uv"`, and a dependency-free Python 3.11+ project. A host supporting that runtime handles Python installation and launching. Hosts that only support older manifests, or do not implement uv execution, should use the wheel and manual stdio configuration instead. No minimum desktop app version is invented or inferred from the manifest version.

Verify the download with the release `SHA256SUMS`, open it in a compatible desktop client, and enter the origin of your existing backend. The optional consumer API key is marked `sensitive` so the host can mask and store it using its credential mechanism. Blank means anonymous discovery; malformed nonempty keys are rejected. The default URL `http://127.0.0.1:8787` is only useful when you already run a backend locally.

The bundle includes only the thin client, a launch wrapper, a minimal project file, manifest, README, security notice, and MIT license. It has no packaged virtual environment, dynamic package dependency, account data, billing server, or executor functions. `python scripts/build_mcpb.py` rebuilds it deterministically and prints the file's SHA-256. Tests extract the archive and run its entry point in a separate process, then exercise initialization, tool discovery, an anonymous backend search, and authentication rejection. A local `uv run` check also verifies the declared launch command; interactive installation in each desktop host remains a separate compatibility check.

Official references: [MCPB manifest and uv runtime](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md), [official uv example](https://github.com/modelcontextprotocol/mcpb/tree/main/examples/hello-world-uv).

## Claude Desktop

Merge [claude-desktop.json](claude-desktop.json) into your Claude Desktop MCP configuration. Use an absolute executable path. For authenticated use on macOS/Linux, append `"--key-file", "/ABSOLUTE/PRIVATE/PATH/guardmarket.key"` to `args`, create the file privately, and set permission 0600. The repository contains no key file. On Windows use the environment mechanism supported by your launcher. Restart the client and inspect its MCP connection status.

## Claude Code

```sh
claude mcp add --transport stdio guardmarket -- /ABSOLUTE/PATH/TO/.venv/bin/guardmarket-mcp --url http://127.0.0.1:8787
claude mcp list
```

Alternatively merge [claude-code.json](claude-code.json) into the project's `.mcp.json`. Provide secrets through the launching shell or the POSIX key-file option. The `.claude-plugin/plugin.json` and root `.mcp.json` support local plugin development after the executable is installed. For example, `claude --plugin-dir /absolute/path/to/guardmarket` loads that local bundle. No official marketplace listing is implied.

## Qwen Code

Merge [qwen-code.json](qwen-code.json) into `.qwen/settings.json`. Set `GUARDMARKET_URL` before launching Qwen Code. For authenticated calls, add `"GUARDMARKET_API_KEY": "${GUARDMARKET_API_KEY}"` to the server's `env` after defining that variable in the launcher environment, or use a POSIX key file. Leave `trust` false so the client's tool approval policy remains in effect.

```sh
qwen mcp list
```

## Qwen-Agent

[qwen-agent.py](qwen-agent.py) constructs an `Assistant` with the public MCP client. Install the optional `qwen-agent[mcp]` dependency separately, then supply the model/provider and marketplace variables documented at the top of that example. The script does not automatically call a skill or spend money.

## Codex

Merge [codex.toml](codex.toml) into your chosen Codex configuration. `env_vars` forwards the named credential variable without embedding its value. The repository includes current portable Agent Plugins `plugin.json` and `mcp.json`, a `skills/guardmarket` workflow, and a `.codex-plugin/plugin.json` compatibility overlay. Install the executable before loading the plugin; local plugin support varies by client surface.

## ChatGPT and Claude web

These remote connectors need a deployed public **HTTPS MCP** endpoint and its configured authorization flow. A GitHub URL, the static Pages URL, and a local stdio process are not remote MCP endpoints. Connect to the operator's actual endpoint only after it has been deployed and verified. Account access, publisher verification, and official directory review remain platform-controlled steps.

## First use

Ask: “Search for a cart-total skill and show the required inputs and current price.” Then, if execution is within your authorization, provide the inputs and spending cap. `market.invoke` requires the exact live skill ID, `arguments`, an 8–100 character `idempotency_key`, and integer `max_price_micros`. Keep the same key and identical arguments when recovering from an uncertain response.

## Official format references

- [Claude Code MCP setup](https://code.claude.com/docs/en/mcp)
- [Claude plugin manifest](https://code.claude.com/docs/en/plugins-reference)
- [Claude remote connectors](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)
- [Qwen Code MCP configuration](https://github.com/QwenLM/qwen-code/blob/main/docs/users/features/mcp.md)
- [Qwen-Agent](https://github.com/QwenLM/Qwen-Agent)
- [Codex MCP configuration](https://developers.openai.com/codex/mcp/)
- [OpenAI portable plugin packaging](https://developers.openai.com/plugins/build/plugins)

Formats reviewed on 2026-09-26. The backend URL, account setup, and application-specific environment handling still need to match the user's deployment.
