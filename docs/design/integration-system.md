# Integration System

**Contract owner for:** how Game Studio integrates with any external system. System-specific interfaces are in [../integrations/](../integrations/).

## 1. Integration boundaries

| System | Direction | Game Studio's side of the boundary |
|---|---|---|
| Paperclip | Bidirectional | Configures Paperclip from studio definitions; (Stage 2) Runtime invoked by Paperclip and calls its REST API |
| Claude Code CLI | Outbound | Launch, configure permissions, read output |
| Codex CLI | Outbound | Same |
| OpenSpec | Outbound (via agents) | Agents run OpenSpec commands/slash-commands in Game Repositories |
| GitHub | Outbound | Clone, fetch, push Task Branches, open PRs (via `git`/`gh`) |
| MCP servers | Outbound (via Providers) | Registered in Provider config; agents call them |

## 2. Adapter responsibilities (Stage 2 code, `PLANNED`)

Each integration that needs code gets one adapter under `integrations/<system>/` (or `runtime/src/launcher/providers/` for Providers). An adapter MUST:

1. Expose a small, Game-Studio-shaped interface (e.g. `ProviderAdapter`, `PaperclipClient`).
2. Translate to and from the external system's formats. External types MUST NOT leak past the adapter.
3. Read configuration and credentials only from the configuration system (§3).
4. Classify errors into the shared error classes (§5).
5. Expose `detect()`/`healthCheck()` for diagnostics.
6. Declare the external version range it supports.

## 3. Integration configuration

| Kind | Where |
|---|---|
| Portable settings (which provider a role prefers, default timeouts) | Framework Repository (agent metadata, example config) |
| Machine settings (paths, URLs like `http://localhost:3100/api`) | `~/.config/game-studio/runtime.yaml` |
| Secrets | Environment / Paperclip secrets / Provider credential stores; never in config files in Git |

## 4. Authentication

| System | Mechanism (`VERIFIED` unless marked) |
|---|---|
| Paperclip (agent) | Bearer token: run JWT injected as `PAPERCLIP_API_KEY` per heartbeat, or long-lived agent API key |
| Paperclip (board) | No auth in `local_trusted` mode; session cookie in `authenticated` mode |
| Claude Code | Subscription login in `~/.claude`, `ANTHROPIC_API_KEY`, or `CLAUDE_CODE_OAUTH_TOKEN` |
| Codex | `$CODEX_HOME/auth.json` (ChatGPT login or API key) |
| GitHub | `GH_TOKEN` / `GITHUB_TOKEN` env for `gh` and HTTPS git (OQ-017 for scoping) |

## 5. Error handling

Shared error classes for all adapters: `unavailable` (cannot reach / not installed), `auth`, `rate_limited`, `conflict`, `invalid_request`, `remote_error`, `timeout`, `unknown`.

| Class | Default policy |
|---|---|
| `unavailable`, `remote_error`, `timeout` | Retry with exponential backoff (3 attempts), then fail the Run |
| `rate_limited` | Do not retry within the Run; report reset time |
| `auth`, `invalid_request` | Fail fast; no retry |
| `conflict` (e.g. Paperclip `409`) | Do not retry; follow the owning workflow |

## 6. Version compatibility

- Each integration document states the version it was verified against.
- On upgrade of an external system, re-run its verification steps and update the document and the dependency registry's `verifiedVersion`.
- Adapters SHOULD check the external version at `detect()` and warn outside the supported range.

## 7. Integration lifecycle

`documented` → `verified` (manual tests pass) → `implemented` (adapter code, Stage 2 only) → `operational` → `deprecated`.

| Integration | Current state |
|---|---|
| Paperclip | documented (from Paperclip repo docs); not installed |
| Claude Code | documented; CLI installed and flags verified |
| Codex | documented; standalone CLI not installed (OQ-009) |
| OpenSpec | documented; CLI installed (1.11.0) |

## Related documents
- [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md) · [../integrations/claude-code-integration.md](../integrations/claude-code-integration.md) · [../integrations/codex-integration.md](../integrations/codex-integration.md) · [../integrations/openspec-integration.md](../integrations/openspec-integration.md)
