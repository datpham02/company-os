# ADR-003: Native Ubuntu Agent Runtime

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-004, ADR-010, [runtime-architecture.md](../architecture/runtime-architecture.md), OQ-013, OQ-027

## Context
Agents need to run AI coding CLIs against game repositories on the studio's machine. That machine runs Ubuntu 24.04 LTS (verified 2026-11-03). Claude Code and Codex authenticate with credentials stored in the user's home directory (`~/.claude`, `~/.codex`). Running them in containers adds credential mounting, file-ownership, and GPU/display complications for game engines and browsers.

## Decision
- The Agent Runtime MUST live in this repository under `runtime/`.
- In v1 it MUST run natively on the user's Ubuntu machine, as the user's own Unix account. Docker MUST NOT be required in v1.
- The Runtime is responsible for: receiving or coordinating Task execution, resolving the target project, preparing working directories, launching Provider CLIs, supervising processes, managing Task Branches and worktrees, collecting logs and results, reporting status to Paperclip, and recovering persisted execution state after a restart.
- The exact Paperclip ↔ Runtime communication mechanism MUST be verified before implementation (OQ-001). See ADR-011.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Docker containers per task | Better isolation but more setup; rejected for v1 simplicity. |
| Cloud sandboxes | Cost, latency, and credential exposure; not needed for a single studio machine. |
| Runtime inside Paperclip (fork) | Violates ADR-002. |

## Consequences
- Isolation relies on Git worktrees, Unix file permissions, and each Provider's own permission/sandbox controls, not on containers ([security-architecture.md](../architecture/security-architecture.md)).
- Agent processes can, in principle, read anything the user account can read. This is an accepted v1 risk with mitigations (OQ-027).
- The machine must have Node.js, Git, the Provider CLIs, and Paperclip installed natively ([ubuntu-setup.md](../operations/ubuntu-setup.md)).

## Reconsider when
- Agents need stronger isolation (untrusted code, third-party contributors), or
- the studio moves to multiple machines or a server, or
- a Provider's native sandbox proves insufficient.
