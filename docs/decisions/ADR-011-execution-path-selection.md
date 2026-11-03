# ADR-011: Staged Execution Path — Paperclip-native First, Runtime via `process` Adapter

- **Status:** Accepted (2026-11-03, after Phase 0)
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-002, ADR-003, ADR-006, ADR-008, ADR-013, C-001, C-002, OQ-001, OQ-002, OQ-003, [paperclip-integration.md](../integrations/paperclip-integration.md)

## Context
ADR-003 (now superseded by ADR-013, which keeps this scope) places a Runtime in this repository that launches Provider CLIs, manages worktrees, and reports to Paperclip. ADR-002 says Game Studio must not duplicate what Paperclip provides.

Research on 2026-11-03 (Paperclip docs at commit `7b8aa60`) found that Paperclip already provides, as `VERIFIED` documented features:

| Capability the brief assigns to the Runtime | Paperclip feature |
|---|---|
| Launch Claude Code / Codex for a task | `claude_local` and `codex_local` adapters spawn the CLIs locally, with session persistence and skills injection |
| Prepare an isolated working directory | Execution workspaces, including isolated `git_worktree` mode with own checkout path and branch |
| Resolve the project's repository | Project workspaces (`cwd`, `repoUrl`, `repoRef`), with managed clones of repo-only workspaces |
| Collect logs and results | Adapters capture stdout, parse usage/cost, record a run record |
| Report status | Agents update issue status and comments through the REST API during the heartbeat |
| Recover after restart | Persisted run records and sessions; heartbeat retry/recovery |
| Approval before completion | Issue execution policies with `review` and `approval` stages |

Paperclip also offers integration points for custom execution: the `process` adapter (runs any command with `PAPERCLIP_*` environment variables), the `http` adapter (webhook), and external adapter plugins.

Building a full Runtime now would duplicate most of the above.

## Decision
1. **Stage 1 (Paperclip-native).** Run Agent Instances on Paperclip's `claude_local` / `codex_local` adapters with Paperclip execution workspaces in `git_worktree` mode. Game Studio supplies role instructions, rules, skills, and project workspace configuration. No Runtime code is written in Stage 1.
2. **Gap analysis.** While operating Stage 1, record every requirement from ADR-013/ADR-006/ADR-009 that Paperclip does not satisfy (for example: Task Branch naming, project-registry resolution, dependency checks, Game Studio rule enforcement, merge gating).
3. **Stage 2 (Runtime for gaps only).** Build the Runtime only for verified gaps. Its preferred entry point is Paperclip's documented `process` adapter: a Paperclip agent with `adapterType: "process"` runs the Runtime command, which receives the Paperclip environment variables, executes, and reports through the REST API. An external adapter plugin is the fallback if richer transcript rendering is needed.
4. In both stages exactly one component owns worktree creation for a given Agent Instance (ADR-006).

## Alternatives considered
| Alternative | Assessment |
|---|---|
| **A. Paperclip-native adapters only** | Least code. Gaps unknown until operated. Chosen as Stage 1. |
| **B. Runtime behind the `process` adapter** | Documented, simple, preserves ADR-013. Unknown: whether the resolved execution-workspace path reaches a `process` agent (OQ-003). Chosen for Stage 2. |
| **C. Runtime as an external adapter plugin** | Richest UI integration; requires following Paperclip's adapter package contract; more coupling to Paperclip internals. Fallback. |
| **D. Runtime as HTTP service behind the `http` adapter** | Adds a long-running local service; conflicts with ADR-004's simplicity. |
| **E. Runtime daemon polling the REST API with an agent API key** | Bypasses heartbeats; duplicates scheduling; loses Paperclip's run records. Rejected. |
| **F. Full Runtime as specified in the brief, ignoring Paperclip adapters** | Violates ADR-002's "do not duplicate". Rejected unless gap analysis justifies it. |

## Consequences
- If accepted, the Runtime's first deliverable becomes a gap analysis, not code. The Runtime design in [runtime-architecture.md](../architecture/runtime-architecture.md) remains the target for Stage 2 but every sub-component is subject to the gap analysis.
- Stage 1 still satisfies ADR-013, which superseded ADR-003 (native Windows, no Docker): Paperclip runs natively and launches the CLIs on the same machine. Paperclip runs on native Windows; its onboarding wizard's sign-in step does not (OQ-031).
- Paperclip's adapter defaults include `dangerouslySkipPermissions: true` for Claude Code. Stage 1 MUST override this according to [security-architecture.md](../architecture/security-architecture.md) (OQ-011).
- **Phase 0 results (2026-11-03) that shape Stage 1 and Stage 2:**
  - Stage 1 works end to end on Windows: `claude_local` agents run in per-Task worktrees, report to Paperclip, and pass review and Board approval stages (OQ-002, OQ-005).
  - Isolated `git_worktree` workspaces need Paperclip's **experimental** instance flag `enableIsolatedWorkspaces`. Stage 1 depends on it; re-check it after every Paperclip upgrade (OQ-008).
  - Under the default ACP engine, `claude_local` approves every tool request, so "Skip permissions" off is not enough. Stage 1 uses the Claude CLI engine profile with the reporting rule (security-architecture.md §4, OQ-011).
  - The `process` adapter receives no Task ID, no workspace path and no workspace cwd; it runs in the Paperclip server's cwd and is retried if it does not update its Task (OQ-003). A Stage 2 Runtime behind `process` MUST resolve its Task (for example `GET /api/heartbeat-runs/{runId}/issues`) and its execution workspace through the API, and MUST update the Task itself. This keeps option B viable but adds work; option C (an adapter plugin) stays the fallback.

## Reconsider when
- Stage 1 shows Paperclip cannot meet a MUST requirement of ADR-006 or ADR-009, or
- Paperclip removes or changes the `process` adapter, or
- the Board Operator prefers a fully independent Runtime regardless of duplication.
