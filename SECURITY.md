# Security and privacy

This public package forwards MCP requests to one operator-selected backend. It contains no account database, payment processor code, admin credentials, or skill executor implementation. It does not collect analytics or send telemetry. The website has no tracking scripts or third-party fonts.

Use only a backend you trust. HTTPS is required except for numeric loopback development addresses. Authorization headers are sent only to that fixed origin. Redirects and inherited proxy configuration are disabled. Input, output, JSON depth and size limits apply. Client errors omit exception text and credentials.

Use consumer API keys with the smallest available access, never administrator credentials. Key files must be owned regular POSIX files with permission 0600, with symlinks rejected. Environment-based keys are supported on all platforms; process owners and the host client may access their process environment.

Skill descriptions and outputs are untrusted data, not instructions. Inspect effect declarations and the actual price before invoking. Avoid sensitive inputs unless the backend operator's data policy supports your purpose. An invocation can spend funds even when its response is lost; retain the original idempotency key.

For a suspected vulnerability, use [GitHub private vulnerability reporting](https://github.com/zma-petterzhang/guardmarket/security/advisories/new) if enabled. Otherwise open an issue asking for a private contact without publishing credentials or exploit details. No paid service availability or security certification is represented by this repository.
