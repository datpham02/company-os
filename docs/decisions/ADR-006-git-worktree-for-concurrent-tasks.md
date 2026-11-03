# ADR-006: Git Worktree for Concurrent Tasks

- **Status:** Accepted. The decision to use worktrees is accepted; *which component creates them* is open (C-001, OQ-002).
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-005, ADR-009, ADR-011, [runtime-architecture.md](../architecture/runtime-architecture.md)

## Context
Several Tasks on the same Game Project can run at once. Running them in one checkout corrupts each other's work. Full clones per task waste disk and network. `git worktree` provides multiple working directories sharing one object store, each on its own branch.

Verified 2026-11-03: Paperclip's execution workspaces support an isolated `git_worktree` mode in which "an isolated execution workspace has its own checkout path, branch, and local runtime instance" (Paperclip docs `guides/board-operator/execution-workspaces-and-runtime-services.md`).

## Decision
- Every Task that changes code MUST run on a dedicated Task Branch, never the Default Branch.
- When two or more Tasks on the same Game Project can run concurrently, each MUST run in its own Task Workspace implemented as a Git worktree of the Primary Checkout.
- Tasks whose changes conflict (same files or an explicit dependency) MUST NOT run concurrently in the same Task Workspace. They SHOULD be serialized; if run in parallel they MUST use separate worktrees and be integrated through review.
- Agents MUST NOT work directly in the Primary Checkout.
- The Task ↔ Task Branch ↔ Task Workspace mapping MUST be recorded and kept after the Run (Runtime Data and/or Paperclip execution-workspace metadata).
- Exactly one component MUST own worktree creation and cleanup for a given Agent Instance. Either Paperclip's execution workspaces or the Runtime Workspace Manager, never both (C-001).

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| One shared checkout, tasks serialized | No parallelism. |
| Full clone per task | Disk/network cost; slower setup. |
| Branch switching in one checkout | Unsafe with concurrent processes. |

## Consequences
- Worktree lifecycle (creation, reuse, cleanup) must be defined ([runtime-architecture.md §6](../architecture/runtime-architecture.md#6-workspace-manager)).
- Worktrees cannot check out the same branch twice; branch naming must be unique per Task.
- Engine projects with large generated caches (e.g. Unity `Library/`) may make worktrees expensive (OQ-022).

## Reconsider when
- A chosen game engine cannot operate in worktrees, or
- containers replace native execution (ADR-003).
