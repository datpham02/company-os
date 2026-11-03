# Architecture Decision Records

ADRs are the highest authority in the documentation hierarchy ([../conventions.md §3](../conventions.md#3-source-of-truth-hierarchy)).

## Process

1. Copy [ADR-000-template.md](ADR-000-template.md) to `ADR-NNN-kebab-title.md` with the next free number.
2. Set status `Proposed`. Proposed ADRs are not binding.
3. The Board Operator accepts or rejects the ADR. Accepted ADRs change only by being superseded by a new ADR.
4. An ADR MUST NOT turn an `UNVERIFIED` assumption into an accepted decision. Link the open question instead.

## Index

| ADR | Title | Status |
|---|---|---|
| [ADR-001](ADR-001-single-game-studio-repository.md) | Single Game Studio repository | Accepted |
| [ADR-002](ADR-002-paperclip-independent-orchestration.md) | Paperclip as independent orchestration platform | Accepted |
| [ADR-003](ADR-003-native-ubuntu-agent-runtime.md) | Native Ubuntu Agent Runtime (no Docker in v1) | Superseded by ADR-013 |
| [ADR-004](ADR-004-task-based-agent-execution.md) | Task-based agent execution | Accepted |
| [ADR-005](ADR-005-independent-game-repositories.md) | Independent game repositories | Accepted |
| [ADR-006](ADR-006-git-worktree-for-concurrent-tasks.md) | Git worktrees for concurrent tasks | Accepted (owner of worktree creation open: C-001) |
| [ADR-007](ADR-007-external-dependency-registry.md) | External dependency registry | Accepted |
| [ADR-008](ADR-008-provider-abstraction.md) | Provider abstraction for Claude Code and Codex | Accepted |
| [ADR-009](ADR-009-approval-before-merge.md) | Approval before Git merge | Accepted |
| [ADR-010](ADR-010-runtime-data-outside-repository.md) | Runtime data outside the main repository | Accepted |
| [ADR-011](ADR-011-execution-path-selection.md) | Staged execution path: Paperclip-native first, Runtime via `process` adapter | **Proposed** |
| [ADR-012](ADR-012-agent-definition-format.md) | Agent definitions aligned with the Agent Companies package format | **Proposed** |
| [ADR-013](ADR-013-native-windows-studio-host.md) | Native Windows studio host (supersedes ADR-003) | Accepted |

ADR-001 to ADR-010 record decisions the Board Operator approved before this documentation was written (the "approved architecture decisions" of the v1 brief). ADR-011 and ADR-012 come from the 2026-11-03 research findings and await a decision.
