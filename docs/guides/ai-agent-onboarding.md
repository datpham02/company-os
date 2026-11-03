# AI Agent Onboarding

Read this first if you are an AI agent that has never seen this repository. Each answer is short and links to the authoritative document.

## 1. What is Game Studio?
A reusable framework for running an AI game studio across many independent games. It defines the studio's organization, agent roles, rules, workflows, project registry, dependency registry, and integration contracts. It also plans a local Agent Runtime (`PLANNED`). It is documentation-only today. → [../architecture/overview.md](../architecture/overview.md)

## 2. What does Paperclip do?
Paperclip is a separate open-source application and the studio's control plane. It handles companies, agents and their reporting tree, projects, tasks (issues) with atomic checkout, heartbeats that wake agents, approvals and review/approval stages, budgets, and the audit log. It can also launch Claude Code and Codex itself through its `claude_local` / `codex_local` adapters. → [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md), [ADR-002](../decisions/ADR-002-paperclip-independent-orchestration.md)

## 3. What does Game Studio own?
The definitions: company, roles (`agents/`), rules (`company/RULES.md`), workflows (`workflows/`), project registry, dependency registry, integration contracts, ADRs, and later the Runtime for gaps Paperclip does not cover. It does not own task tracking, assignment, or approvals; Paperclip does. → [../architecture/system-components.md](../architecture/system-components.md)

## 4. How does an agent execute a task?
Paperclip wakes the assigned Agent Instance with a heartbeat. The executor prepares a Task Workspace (git worktree on a Task Branch) and launches the Provider CLI there. In Stage 1 the executor is Paperclip's adapter; in Stage 2 it is the Game Studio Runtime (`PLANNED`). The agent checks out the Task, implements, tests, pushes the branch, opens a PR, comments, and moves the Task to `in_review`. → [../../workflows/development-cycle.md](../../workflows/development-cycle.md), [../architecture/runtime-architecture.md](../architecture/runtime-architecture.md), [ADR-011](../decisions/ADR-011-execution-path-selection.md) (`PROPOSED`)

## 5. Where does game source code live?
Only in each game's own repository, e.g. `datpham02/node-arena`. Never in this repository. Games are listed in [../../projects/project-registry.yaml](../../projects/project-registry.yaml) (empty today). → [ADR-005](../decisions/ADR-005-independent-game-repositories.md), [../architecture/repository-architecture.md](../architecture/repository-architecture.md)

## 6. How is a new game created?
`game-director` proposes it and the Board approves. The Board creates the GitHub repository with branch protection and the Paperclip project. `producer` adds the registry entry, and an implementer seeds `AGENTS.md`/`CLAUDE.md` and the engine skeleton. `game-designer` writes the pillars. → [../../workflows/project-initialization.md](../../workflows/project-initialization.md)

## 7. How are external dependencies managed?
They are registered in [../../dependencies/registry.yaml](../../dependencies/registry.yaml) with source, license, version constraint, install reference, and status (`candidate` → `evaluating` → `approved` → `integrated`). They are never copied into this repository. Installation needs Board approval. → [../design/dependency-system.md](../design/dependency-system.md), [../../workflows/add-external-dependency.md](../../workflows/add-external-dependency.md)

## 8. How does Git workspace isolation work?
Every code Task gets its own Task Branch. Concurrent Tasks on the same game each get their own git worktree. Agents never work in the Primary Checkout or on the Default Branch. Exactly one component (Paperclip or the Runtime) owns worktree creation; which one is open (C-001). → [ADR-006](../decisions/ADR-006-git-worktree-for-concurrent-tasks.md), [../architecture/runtime-architecture.md §6](../architecture/runtime-architecture.md#6-workspace-manager), [../../workflows/parallel-tasks.md](../../workflows/parallel-tasks.md)

## 9. How are approvals handled?
Governed actions (new project, dependency, release, hire, budget, permission bypass) use Paperclip approvals decided by the Board Operator. Code merges need a `qa` review stage, then a Board approval stage in Paperclip **and** an approval on the GitHub PR. Only the Board merges. → [ADR-009](../decisions/ADR-009-approval-before-merge.md), [../../workflows/approval-request.md](../../workflows/approval-request.md), [../../workflows/code-review-and-merge.md](../../workflows/code-review-and-merge.md)

## 10. Where should implementation begin?
Not with Runtime code. Begin with Phase 0 of the roadmap: install Paperclip and the standalone Codex CLI, then run the verification experiments that close the blocking open questions (OQ-001, OQ-002, OQ-003, OQ-011). After that, operate Stage 1 and do the gap analysis. → [implementation-roadmap.md](implementation-roadmap.md)

## Rules you must not break
[../../company/RULES.md](../../company/RULES.md) applies to every Run. If you work on this repository itself, also follow [../../AGENTS.md](../../AGENTS.md).

## Vocabulary
Use [../glossary.md](../glossary.md) terms exactly. Check status labels ([../conventions.md](../conventions.md)): do not rely on `UNVERIFIED` behaviour, and never run a `PLANNED` command.
