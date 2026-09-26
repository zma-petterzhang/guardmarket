# Validation record — 2026-09-26

Public client version: 0.3.0. Catalog snapshot: 125 unique builtin skill contracts, version 1.0.0. This report covers the public distribution; it does not certify an independently deployed backend or claim vendor-directory acceptance.

- 27 Python unittest cases passed under Python 3.12. The CI matrix additionally runs Python 3.11, 3.12, and 3.13 after publication.
- Anonymous search and description succeeded against an existing local test backend. No account credentials were needed and no paid invocation was performed for this distribution check.
- A controlled HTTP fixture verified authenticated invocation preserves the exact spending cap, arguments, and idempotency key; anonymous private-tool requests fail before making a network call.
- Invalid origins, credentials, input schemas, malformed/non-finite JSON, redirects, inherited proxies, unsafe key-file modes, and key-file symlinks were covered by tests.
- Stdio initialization, tool listing, tool execution, and pre-initialization rejection were verified.
- All 125 catalog input and expected-output examples conform to their declared schemas. These schema checks do not execute the private backend functions; runtime skill implementation validation belongs to that backend's test suite.
- A separate integration run connected this public `Client` to a temporary GuardMarket test backend and executed all 125 catalog examples. All outputs matched; repeated requests with the same idempotency keys did not create additional charges. Total settled charges were 1,250,000 simulated micros. This was an actual backend execution check, separate from the static schema tests; existing user-created skill records were not changed.
- All 130 generated HTML pages and their internal asset/link targets were checked. Desktop and mobile pages were rendered in real Chrome via Playwright. Search found the cart-total skill; CSV category filtering showed six entries; no browser errors or mobile horizontal overflow occurred.
- Portable plugin and MCP manifests passed the official Agent Plugins 1.0.0 JSON schemas. The Codex compatibility manifest passed the bundled plugin validator; the skill passed the bundled skill validator.
- Wheel and source distributions built successfully. The wheel installed into an isolated environment and `guardmarket-mcp --version` returned 0.3.0. Archive members were checked to exclude backend, billing, executor, state, credential, and local artifact files.
- A deterministic MCPB 0.4 bundle was built using the uv runtime and an explicit 10-file allowlist. Its manifest passed the official v0.4 schema. After extraction, its actual entry point completed MCP initialization, listed all five tools, searched a controlled backend anonymously with a blank optional key, and rejected anonymous wallet access. The declared `uv run --directory ... server.py` command was also exercised locally. Interactive installation in each desktop host has not been asserted.
- Six registry-preparation tests cover release identity, bundle metadata and artifact checksums. The manual registry workflow uses GitHub OIDC after release publication; this validation report does not itself assert that a registry submission succeeded.

The repository includes official-format examples for Claude Desktop/Code, Qwen Code/Agent, and Codex. Authenticated end-to-end interactions inside each vendor application have not been asserted. PyPI publishing, permanent public MCP deployment, OAuth production operation, and official directory review are separate release/operator steps.
