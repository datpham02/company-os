# ADR-010: Runtime Data Outside the Main Repository

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-003, [repository-architecture.md](../architecture/repository-architecture.md), [configuration.md](../operations/configuration.md)

## Context
Execution produces logs, transcripts, run state, Task Workspaces, and caches. They are machine-specific, large, may contain secrets, and change constantly.

## Decision
- Runtime Data MUST NOT be stored in, or committed to, the Framework Repository or any Game Repository.
- Runtime Data MUST live under user-level directories outside the repository. Default locations (`PROPOSED`, configurable):

  | Data | Default location |
  |---|---|
  | Runtime configuration | `~/.config/game-studio/` |
  | Run state, logs, transcripts | `~/.local/state/game-studio/` |
  | Primary Checkouts and Task Workspaces | `~/game-studio-workspace/` |

- Machine-specific values (absolute paths, credentials, ports) MUST live in local configuration, not in versioned files.
- Versioned files MAY reference Runtime Data only by logical identifiers (Project ID, Task Key, run ID).

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| `runtime/data/` inside the repo with `.gitignore` | Easy to commit by accident; mixes machine state with source. |
| Store everything in Paperclip | Paperclip stores run records but not Game Studio's local workspace state; also couples recovery to Paperclip availability. |

## Consequences
- Backup must cover these directories separately ([backup-and-recovery.md](../operations/backup-and-recovery.md)).
- When Paperclip owns execution workspaces (ADR-011 path A), their location is set by Paperclip, not by this ADR (OQ-002).

## Reconsider when
- The Runtime runs on more than one machine and needs shared state.
