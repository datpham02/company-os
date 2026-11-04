# AI Agent Onboarding

Read this first if you are an AI agent that has never seen this repository. Each answer is short and links to the authoritative document.

## 1. What is Company OS?
The framework of an AI-operated company with departments (today Game and Web). It defines the Company Core, each department's roles and knowledge, the project and dependency registries, and how the company is built in Paperclip. Start with [../../knowledge/README.md](../../knowledge/README.md) for operating knowledge and [../README.md](../README.md) for engineering documentation.

## 2. What does Paperclip do?
Paperclip is a separate open-source application and the studio's control plane. It handles companies, agents and their reporting tree, projects, tasks (issues) with atomic checkout, heartbeats that wake agents, approvals and review/approval stages, budgets, and the audit log. It can also launch Claude Code and Codex itself through its `claude_local` / `codex_local` adapters. → [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md), [ADR-002](../decisions/ADR-002-paperclip-independent-orchestration.md)

## 3. What does Company OS own?
The definitions: company, roles (`knowledge/company/agents/`), rules (`knowledge/company/policies/rules.md`), workflows (`knowledge/company/workflows/`), project registry, dependency registry, integration contracts, ADRs, and later the Runtime for gaps Paperclip does not cover. It does not own task tracking, assignment, or approvals; Paperclip does. → [../architecture/system-components.md](../architecture/system-components.md)

## 4. How does an agent execute a task?
Paperclip wakes the assigned Agent Instance with a heartbeat. The executor prepares a Task Workspace (git worktree on a Task Branch) and launches the Provider CLI there. In Stage 1 the executor is Paperclip's adapter; in Stage 2 it is the Game Studio Runtime (`PLANNED`). The agent checks out the Task, implements, tests, pushes the branch, opens a PR, comments, and moves the Task to `in_review`. → [../../knowledge/company/workflows/development-cycle.md](../../knowledge/company/workflows/development-cycle.md), [../architecture/runtime-architecture.md](../architecture/runtime-architecture.md), [ADR-011](../decisions/ADR-011-execution-path-selection.md) (accepted)

## 5. Where does project source code live?
Only in each game's own repository, e.g. `datpham02/node-arena`. Never in this repository. Games are listed in [../../projects/project-registry.yaml](../../knowledge/projects/registry.yaml) (empty today). → [ADR-005](../decisions/ADR-005-independent-game-repositories.md), [../architecture/repository-architecture.md](../architecture/repository-architecture.md)

## 6. How is a new project created?
`director` proposes it and the Board approves. The Board creates the GitHub repository with branch protection and the Paperclip project. `producer` adds the registry entry, and an implementer seeds `AGENTS.md`/`CLAUDE.md` and the engine skeleton. `game-designer` writes the pillars. → [../../knowledge/company/workflows/project-initialization.md](../../knowledge/company/workflows/project-initialization.md)

## 7. How are external dependencies managed?
They are registered in [../../dependencies/registry.yaml](../../dependencies/registry.yaml) with source, license, version constraint, install reference, and status (`candidate` → `evaluating` → `approved` → `integrated`). They are never copied into this repository. Installation needs Board approval. → [../design/dependency-system.md](../design/dependency-system.md), [../../knowledge/company/workflows/add-external-dependency.md](../../knowledge/company/workflows/add-external-dependency.md)

## 8. How does Git workspace isolation work?
Every code Task gets its own Task Branch. Concurrent Tasks on the same game each get their own git worktree. Agents never work in the Primary Checkout or on the Default Branch. Exactly one component (Paperclip or the Runtime) owns worktree creation; which one is open (C-001). → [ADR-006](../decisions/ADR-006-git-worktree-for-concurrent-tasks.md), [../architecture/runtime-architecture.md §6](../architecture/runtime-architecture.md#6-workspace-manager), [../../knowledge/company/workflows/parallel-tasks.md](../../knowledge/company/workflows/parallel-tasks.md)

## 9. How are approvals handled?
Governed actions (new project, dependency, release, hire, budget, permission bypass) use Paperclip approvals decided by the Board Operator. Code merges need a `qa` review stage, then a Board approval stage in Paperclip **and** an approval on the GitHub PR. Only the Board merges. → [ADR-009](../decisions/ADR-009-approval-before-merge.md), [../../knowledge/company/workflows/approval-request.md](../../knowledge/company/workflows/approval-request.md), [../../knowledge/company/workflows/code-review-and-merge.md](../../knowledge/company/workflows/code-review-and-merge.md)

## 10. Where should implementation begin?
Not with Runtime code. Begin with Phase 0 of the roadmap: install Paperclip and the standalone Codex CLI, then run the verification experiments that close the blocking open questions (OQ-001, OQ-002, OQ-003, OQ-011). After that, operate Stage 1 and do the gap analysis. → [phases.md](../roadmap/phases.md)

## Rules you must not break
[../../knowledge/company/policies/rules.md](../../knowledge/company/policies/rules.md) applies to every Run. If you work on this repository itself, also follow [../../AGENTS.md](../../AGENTS.md).

## Vocabulary
Use [../vision/terminology.md](../vision/terminology.md) terms exactly. Check status labels ([../conventions.md](../conventions.md)): do not rely on `UNVERIFIED` behaviour, and never run a `PLANNED` command.
