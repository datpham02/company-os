# Game Studio Documentation

**Documentation version:** Architecture v1.0 · **Framework version:** see [../VERSION](../VERSION) · **Implementation status:** documentation only; no Runtime code exists.

This is the central index. Every document in the repository is reachable from here.

## 1. What Game Studio is

Game Studio is a reusable framework for running an AI-powered, multi-project game studio. It defines:

- the **studio organization**: company, agent roles, reporting lines, decision authority;
- the **rules and workflows** agents follow;
- the **project registry**: which games exist and where their independent repositories are;
- the **dependency registry**: which external tools the studio uses;
- the **integration contracts** with Paperclip, Claude Code, Codex, Cursor CLI, and OpenSpec;
- a **local Agent Runtime** (`PLANNED`) that executes tasks on the studio's Windows machine.

**Paperclip**, an independent application, is the control plane. It runs the company day to day: agents, projects, tasks, assignment, approvals, and execution coordination. Game Studio defines *what the studio is and how it works*. Paperclip *operates* it. Game code lives in separate repositories, one per game.

## 2. Architectural principles

1. **Do not duplicate Paperclip.** Game Studio integrates with Paperclip and does not re-implement it ([ADR-002](decisions/ADR-002-paperclip-independent-orchestration.md)).
2. **One framework, many games.** The framework repository holds no game code. Each game has its own repository ([ADR-001](decisions/ADR-001-single-game-studio-repository.md), [ADR-005](decisions/ADR-005-independent-game-repositories.md)).
3. **Provider independence.** Agent roles are not tied to one AI CLI ([ADR-008](decisions/ADR-008-provider-abstraction.md)).
4. **Isolation by default.** Each task works on its own branch, in its own workspace when needed ([ADR-006](decisions/ADR-006-git-worktree-for-concurrent-tasks.md)).
5. **Humans approve merges.** No agent merges unreviewed work ([ADR-009](decisions/ADR-009-approval-before-merge.md)).
6. **Register, don't vendor.** External tools are referenced, never copied in ([ADR-007](decisions/ADR-007-external-dependency-registry.md)).
7. **Runtime data stays local.** Logs, state, and worktrees live outside the repository ([ADR-010](decisions/ADR-010-runtime-data-outside-repository.md)).
8. **Verified claims only.** Unverified behaviour is labelled `UNVERIFIED` and tracked in [open-questions.md](roadmap/open-questions.md).

## 3. Reading order

| You are… | Read in this order |
|---|---|
| **An AI agent new to the repo** | [guides/ai-agent-onboarding.md](guides/ai-agent-onboarding.md) → [terminology.md](vision/terminology.md) → [architecture/overview.md](architecture/overview.md) → the documents for your task |
| **The Board Operator** | [architecture/overview.md](architecture/overview.md) → [decisions/README.md](decisions/README.md) → [roadmap/open-questions.md](roadmap/open-questions.md) → [operations/installation.md](operations/installation.md) |
| **An implementer of the Runtime** | [roadmap/phases.md](roadmap/phases.md) → [architecture/runtime-architecture.md](architecture/runtime-architecture.md) → [integrations/paperclip-integration.md](integrations/paperclip-integration.md) → [architecture/security-architecture.md](architecture/security-architecture.md) |
| **Defining agents or workflows** | [design/company-design.md](design/company-design.md) → [design/agent-system.md](design/agent-system.md) → [design/workflow-system.md](design/workflow-system.md) |

## 4. Authority

The hierarchy below is defined in [conventions.md §3](conventions.md#3-source-of-truth-hierarchy). Higher entries win.

1. Accepted ADRs → 2. Architecture → 3. Design → 4. Workflows → 5. Integrations → 6. Operations → 7. READMEs and guides.

Conflicts are never resolved silently. They are logged in [architecture/open-questions.md § Conflicts](roadmap/open-questions.md#conflicts).

## 5. Document map

### Foundations
- [conventions.md](conventions.md): normative terms, status labels, hierarchy, ownership, naming.

### Vision (`vision/`)
- [terminology.md](vision/terminology.md): the single definition of every term.

### Architecture (`architecture/`)
- [overview.md](architecture/overview.md): vision, components, flows, boundaries.
- [system-components.md](architecture/system-components.md): contract per component (purpose, inputs, outputs, must-not).
- [repository-architecture.md](architecture/repository-architecture.md): repositories, directories, Git vs. local data.
- [runtime-architecture.md](architecture/runtime-architecture.md): Runtime lifecycle, sub-components, recovery, concurrency (`PLANNED`).
- [data-flow.md](architecture/data-flow.md): what flows between Paperclip, Game Studio, Runtime, providers, Git, tools.
- [security-architecture.md](architecture/security-architecture.md): credentials, permissions, approval boundaries.
- [stage1-gap-analysis.md](architecture/stage1-gap-analysis.md): requirements Paperclip did not meet in Stage 1, and the response to each.
- [company-os-migration-map.md](architecture/company-os-migration-map.md): file-by-file restructure into `knowledge/` and departments (M1 done 2026-11-05).

### Design (`design/`)
- [company-design.md](design/company-design.md): organization, hierarchy, decision authority.
- [agent-system.md](design/agent-system.md): agent definition contract; role vs. provider vs. skill vs. tool vs. workflow.
- [workflow-system.md](design/workflow-system.md): workflow structure, triggers, gates, retries.
- [project-system.md](design/project-system.md): project registration, configuration, lifecycle, isolation.
- [dependency-system.md](design/dependency-system.md): dependency registry, categories, versions, licenses.
- [integration-system.md](design/integration-system.md): integration boundaries and adapter responsibilities.
- [review-package.md](design/review-package.md): `PROPOSED` diff handoff to a read-only reviewer (OQ-042).

### Integrations (`integrations/`)
- [paperclip-integration.md](integrations/paperclip-integration.md)
- [claude-code-integration.md](integrations/claude-code-integration.md)
- [codex-integration.md](integrations/codex-integration.md)
- [cursor-integration.md](integrations/cursor-integration.md)
- [openspec-integration.md](integrations/openspec-integration.md)

### Decisions (`decisions/`)
- [decisions/README.md](decisions/README.md): ADR index and process.

### Operations (`operations/`)
- [windows-setup.md](operations/windows-setup.md), [installation.md](operations/installation.md), [company-bootstrap.md](operations/company-bootstrap.md), [configuration.md](operations/configuration.md), [runtime-management.md](operations/runtime-management.md), [logging-and-debugging.md](operations/logging-and-debugging.md), [backup-and-recovery.md](operations/backup-and-recovery.md), [troubleshooting.md](operations/troubleshooting.md), [security-operations.md](operations/security-operations.md), [review-package-runbook.md](operations/review-package-runbook.md) (Phase 6 pilot, `PROPOSED`)

### Guides (`guides/`)
- [ai-agent-onboarding.md](guides/ai-agent-onboarding.md): answers the ten orientation questions every new agent needs.

### Roadmap (`roadmap/`)
- [phases.md](roadmap/phases.md): what to build, in what order, and what must be verified first.
- [open-questions.md](roadmap/open-questions.md): unverified assumptions (`OQ-NNN`) and conflicts (`C-NNN`).

### Company knowledge (`../knowledge/`, ADR-019)
- [../knowledge/README.md](../knowledge/README.md): scopes and loading order.
- [../knowledge/company/README.md](../knowledge/company/README.md): Company Core: COMPANY, ORGANIZATION, OPERATING_MODEL, policies (rules, provider allocation), standards (task contract), shared roles, company workflows, cross-department contracts (game–platform contract).
- [../knowledge/departments/README.md](../knowledge/departments/README.md): Game and Web charters, department roles, workflows and domain rules.
- [../knowledge/projects/README.md](../knowledge/projects/README.md): project registry, schema and entrypoints.

### Outside `docs/` and `knowledge/`
- [../dependencies/](../dependencies/): external dependency registry.
- [../config/](../config/), [../scripts/](../scripts/): Paperclip agent configuration, setup and maintenance scripts.
- [../runtime/README.md](../runtime/README.md): Runtime gap filler and start script; the Runtime itself is `PLANNED`.

## 6. How AI agents should navigate

1. Start at [guides/ai-agent-onboarding.md](guides/ai-agent-onboarding.md). It links to the authoritative answer for each core question.
2. Before acting on a claim about an external system, check its status label. Do not rely on `UNVERIFIED` behaviour; consult [open-questions.md](roadmap/open-questions.md).
3. Before proposing an architectural change, read the relevant ADR. Accepted ADRs are binding.
4. When documents disagree, apply [conventions.md §3](conventions.md#3-source-of-truth-hierarchy) and log the conflict.
5. Use [terminology.md](vision/terminology.md) terms exactly. "Task" means a Paperclip issue; "Run" means one CLI process execution.
