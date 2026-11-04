# ADR-002: Paperclip as Independent Orchestration Platform

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-011, [paperclip-integration.md](../integrations/paperclip-integration.md), OQ-001, OQ-008

## Context
The studio needs company management, agent registration, a project and task tracker, assignment, approvals, and execution coordination. Paperclip ([paperclipai/paperclip](https://github.com/paperclipai/paperclip), MIT) is an open-source Node.js server and React UI that provides these. Its documentation (verified at commit `7b8aa60`, 2026-11-03) describes companies, agents in a reporting tree, issues with atomic checkout, heartbeats, approvals, execution policies, budgets, an activity log, a REST API, and adapters that launch Claude Code and Codex locally.

## Decision
- Paperclip MUST be used as an independent application. It MUST NOT be forked into, vendored into, or developed inside the Game Studio repository.
- Paperclip owns: company and organization records, agent registration and status, projects, tasks (issues), assignment, task status, approvals, heartbeat scheduling, budgets, and the audit log.
- Game Studio owns: the *definitions* that Paperclip is configured from (roles, rules, workflows, project registry, dependencies) and any execution capability Paperclip lacks.
- Game Studio MUST NOT re-implement a capability Paperclip provides unless a documented integration gap requires it. Every such gap MUST be recorded in [open-questions.md](../roadmap/open-questions.md) or an ADR.
- Game Studio MUST use only Paperclip interfaces that are documented by Paperclip (REST API, CLI, adapters, plugin system, company import/export).

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Build a custom orchestrator in Game Studio | Duplicates mature functionality; large effort. |
| Fork Paperclip | Ongoing merge burden; couples studio to a fork. |
| No orchestrator (manual CLI sessions) | Doesn't meet the goal of managing the studio without opening game workspaces. |

## Consequences
- Paperclip's version and API stability become a dependency risk (OQ-008).
- Game Studio's value is concentrated in studio definitions, game-specific conventions, and integration glue.
- Because Paperclip already launches Claude Code and Codex and manages git-worktree workspaces, the scope of the Game Studio Runtime must be justified against Paperclip's built-in behaviour (ADR-011, C-001).

## Reconsider when
- Paperclip changes license, is abandoned, or breaks its API without a migration path, or
- the studio needs capabilities Paperclip explicitly declines to support.
