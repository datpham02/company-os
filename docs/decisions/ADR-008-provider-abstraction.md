# ADR-008: Provider Abstraction for Claude Code and Codex

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-004, ADR-011, [claude-code-integration.md](../integrations/claude-code-integration.md), [codex-integration.md](../integrations/codex-integration.md)

## Context
v1 supports two AI coding CLIs: Claude Code and Codex. They differ in flags, output formats, permission models, authentication, and session handling (verified from each CLI's `--help`, 2026-11-03). More CLIs may follow.

## Decision
- Agent Roles MUST NOT depend on a specific Provider. Provider choice is configuration of an Agent Instance.
- Execution code MUST go through a Provider abstraction with one adapter per Provider. The interface is defined in [runtime-architecture.md §5](../architecture/runtime-architecture.md#5-agent-launcher-and-provider-abstraction).
- v1 Providers: Claude Code CLI (`claude_local`) and Codex CLI (`codex_local`). Provider IDs match Paperclip adapter type keys where one exists.
- Provider-specific behaviour (flags, output parsing, auth checks, error classification) MUST live only in that Provider's adapter.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Hardcode Claude Code | Locks the studio to one vendor; Codex already required. |
| Use only Paperclip's adapters with no abstraction of our own | Viable for execution path A in ADR-011. The abstraction is still needed if the Runtime launches CLIs itself. |

## Consequences
- Adding a Provider is a defined workflow ([add-execution-provider.md](../../knowledge/company/workflows/add-execution-provider.md)).
- Lowest-common-denominator risk: features only one Provider has must be optional capabilities.
- If ADR-011 path A is used, Paperclip's adapters *are* the provider abstraction and the Runtime adapter interface is deferred.

## Reconsider when
- A Provider exposes a stable SDK/protocol (e.g. ACP) that makes per-CLI adapters unnecessary.
