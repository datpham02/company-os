# System Components

This document owns the contract of every component. Each section lists **Purpose, Responsibilities, Inputs, Outputs, Dependencies, Must not**, and **Status**. Runtime sub-components are summarised here and detailed in [runtime-architecture.md](runtime-architecture.md).

---

## 1. Paperclip

| | |
|---|---|
| **Purpose** | Control plane that operates the studio as a company of AI agents. |
| **Responsibilities** | Company records; agent registration, reporting tree, status, budgets; projects and project workspaces; tasks (issues), assignment, atomic checkout, status lifecycle; heartbeat scheduling and run records; approvals and issue execution policies (review/approval stages); activity audit log; secrets store; adapters that invoke agent runtimes. |
| **Inputs** | Board Operator actions in the web UI; agent REST API calls during heartbeats; company packages via `company import`; adapter results. |
| **Outputs** | Heartbeat invocations of adapters (with `PAPERCLIP_*` environment variables); task, approval, and run records; REST API responses. |
| **Dependencies** | Node.js 24.11+; embedded PostgreSQL (default) or external PostgreSQL; installed Provider CLIs for local adapters. All `VERIFIED` from Paperclip docs at `7b8aa60`. |
| **Must not** | Be modified or forked by Game Studio (ADR-002). |
| **Status** | External application. Not installed on the studio machine as of 2026-11-03. |

Interface details: [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md).

---

## 2. Game Studio Core

| | |
|---|---|
| **Purpose** | Single source of truth for *what the studio is*: identity, organization, rules, operating model. |
| **Responsibilities** | Maintain [../../knowledge/company/](../../knowledge/company/) files; define decision authority and approval policy; version the studio definition (VERSION, CHANGELOG). |
| **Inputs** | Board Operator decisions; accepted ADRs. |
| **Outputs** | Markdown definitions consumed by agents, by Paperclip setup ([company-design.md](../design/company-design.md)), and by the Runtime. |
| **Dependencies** | None at runtime. |
| **Must not** | Contain game-specific business logic or game source code; contain secrets or machine-specific paths. |
| **Status** | Documented (the files exist). No automation reads them yet. |

---

## 3. Agent Definitions

| | |
|---|---|
| **Purpose** | Reusable, provider-independent definition of each Agent Role. |
| **Responsibilities** | Define ID, name, role, mission, responsibilities, authority, capabilities, tools, inputs, outputs, constraints, collaboration, escalation, success criteria. |
| **Inputs** | [agent-system.md](../design/agent-system.md) contract; [../../knowledge/company/ORGANIZATION.md](../../knowledge/company/ORGANIZATION.md). |
| **Outputs** | `knowledge/company/agents/<agent-id>/AGENTS.md`, used as (a) the instruction body given to the Provider at Run time, (b) the source for registering Agent Instances in Paperclip. |
| **Dependencies** | Skills and Tools named in each definition must be registered in [dependencies/registry.yaml](../../dependencies/registry.yaml) before use. |
| **Must not** | Name a specific Provider as mandatory; contain adapter config, secrets, or absolute paths (ADR-012). |
| **Status** | 7 roles defined. Format accepted (ADR-012); imported into Paperclip on 2026-11-03. |

---

## 4. Workflow definitions ("workflow orchestration")

| | |
|---|---|
| **Purpose** | Describe repeatable studio processes with explicit gates. |
| **Responsibilities** | Define trigger, inputs, actors, steps, outputs, failure cases, approval requirements for each workflow. |
| **Inputs** | [workflow-system.md](../design/workflow-system.md); company rules. |
| **Outputs** | `workflows/*.md`, followed by agents and humans. Executed as Paperclip tasks, sub-tasks, and execution-policy stages. |
| **Dependencies** | Paperclip for task state and gates. |
| **Must not** | Be implemented as a separate workflow *engine* in v1. Paperclip's task hierarchy, heartbeats, and execution policies are the execution mechanism; Game Studio only defines the process. A dedicated engine requires an ADR. |
| **Status** | 12 workflows documented. |

---

## 5. Project Registry

| | |
|---|---|
| **Purpose** | Map each Game Project to its repository, configuration, and Paperclip project. |
| **Responsibilities** | Hold one entry per Game Project ([projects/project-registry.yaml](../../knowledge/projects/registry.yaml)); validate entries against [projects/project-config.schema.yaml](../../knowledge/projects/project-config.schema.yaml). |
| **Inputs** | [project-initialization.md](../../knowledge/company/workflows/project-initialization.md), [register-existing-repository.md](../../knowledge/company/workflows/register-existing-repository.md). |
| **Outputs** | Project ID → repository URL, default branch, engine, enabled agents, dependencies, workflow overrides, Paperclip project ID. |
| **Dependencies** | GitHub (repository exists); Paperclip (project exists). |
| **Must not** | Contain local absolute paths or credentials (those belong in local Runtime config, ADR-010). |
| **Status** | Empty registry; schema `PROPOSED`. Contract: [project-system.md](../design/project-system.md). |

---

## 6. Dependency Registry

| | |
|---|---|
| **Purpose** | Record every external tool the studio may use, without copying it. |
| **Responsibilities** | Hold one entry per Dependency with source, category, version constraint, install reference, required/optional, integration status, compatibility, license. |
| **Inputs** | [add-external-dependency.md](../../knowledge/company/workflows/add-external-dependency.md). |
| **Outputs** | [dependencies/registry.yaml](../../dependencies/registry.yaml); used by setup docs, agents, and (later) Runtime validation. |
| **Dependencies** | None. |
| **Must not** | Vendor external source (ADR-007); imply that a listed dependency is approved for installation. |
| **Status** | Candidate entries recorded. Contract: [dependency-system.md](../design/dependency-system.md). |

---

## 7. Integrations

| | |
|---|---|
| **Purpose** | Define how Game Studio talks to each external system, and (later) hold adapter code. |
| **Responsibilities** | Document verified interfaces, auth, failure modes, version compatibility; later implement adapters under `integrations/<system>/`. |
| **Inputs** | Official documentation; installed tools. |
| **Outputs** | [../integrations/](../integrations/) documents; `PLANNED` adapter code. |
| **Must not** | Invent interfaces; leak one system's types into another's adapter. |
| **Status** | Documented. `integrations/` code directory not created. Contract: [integration-system.md](../design/integration-system.md). |

---

## 8. Agent Runtime

| | |
|---|---|
| **Purpose** | Execute Tasks locally on the studio's Windows machine, where Paperclip's built-in execution is insufficient (ADR-013, ADR-011). |
| **Responsibilities** | Receive a Run request; resolve project; prepare Task Workspace; launch Provider; supervise; collect logs/results; report to Paperclip; persist state; recover after restart. |
| **Inputs** | Run request (from Paperclip `process` adapter environment in the proposed design); project registry; local Runtime config; agent definition. |
| **Outputs** | Commits on Task Branch; Run record in Runtime Data; status/comments in Paperclip; exit code to the invoking adapter. |
| **Dependencies** | Paperclip REST API; Git; Provider CLIs; GitHub. |
| **Must not** | Hardcode game-specific logic; touch the Default Branch; merge; store data in the repository; duplicate Paperclip features without a recorded gap. |
| **Status** | `PLANNED`. Scope subject to ADR-011 gap analysis. |

Sub-components 9–12 belong to the Runtime.

## 9. Dispatcher (Runtime)

| | |
|---|---|
| **Purpose** | Turn an incoming Run request into an execution decision. |
| **Responsibilities** | Validate request; resolve Project ID and Agent Role; check concurrency limits and conflicts; allocate a run ID; hand off to Workspace Manager and Agent Launcher; persist the run record. |
| **Inputs** | `PAPERCLIP_AGENT_ID`, `PAPERCLIP_TASK_ID`, `PAPERCLIP_RUN_ID`, and related environment variables (names `VERIFIED` from Paperclip docs; delivery to `process` adapters `UNVERIFIED`, OQ-003). |
| **Outputs** | Run plan (project, workspace, provider, limits) or a rejection with reason. |
| **Must not** | Assign Tasks (Paperclip does); run two Runs in the same Task Workspace concurrently. |

## 10. Workspace Manager (Runtime)

| | |
|---|---|
| **Purpose** | Provide an isolated working directory for each Task. |
| **Responsibilities** | Ensure Primary Checkout exists and is fetched; create/reuse/clean up Git worktrees; enforce one-Run-per-workspace lock. |
| **Inputs** | Project entry; Task Key; local Workspace Root. |
| **Outputs** | Absolute path to Task Workspace on the correct Task Branch. |
| **Must not** | Operate in the Primary Checkout's working tree for task work; delete a worktree with uncommitted changes without preserving them. |

## 11. Git Manager (Runtime)

| | |
|---|---|
| **Purpose** | Perform Git operations under the safety rules. |
| **Responsibilities** | Branch naming and creation; fetch; status/diff collection; push Task Branch; open PR (via `gh`, `PLANNED`); record Task ↔ Branch ↔ PR mapping. |
| **Must not** | Push to or merge into the Default Branch; force-push; rewrite published history; delete remote branches it did not create. |

## 12. Result Reporter (Runtime)

| | |
|---|---|
| **Purpose** | Make Run outcomes visible in Paperclip. |
| **Responsibilities** | Post Run summary comments; update Task status within allowed transitions; attach branch/PR links; retry reporting with backoff; queue reports while Paperclip is unreachable. |
| **Must not** | Mark a Task `done` when an approval stage is pending; call undocumented endpoints. |

## 13. Agent Launcher and AI Execution Providers

| | |
|---|---|
| **Purpose** | Start, supervise, and stop one Provider CLI process per Run. |
| **Responsibilities** | Build the invocation through a Provider Adapter; set cwd, env, prompt; enforce timeout and grace kill; stream and store output; classify exit. |
| **Providers (v1)** | Claude Code CLI (`claude_local`): [claude-code-integration.md](../integrations/claude-code-integration.md). Codex CLI (`codex_local`): [codex-integration.md](../integrations/codex-integration.md). |
| **Must not** | Pass secrets on the command line; enable a "bypass all permissions" mode unless the security policy for that Agent Instance allows it. |

## Related documents
- [overview.md](overview.md) · [runtime-architecture.md](runtime-architecture.md) · [../design/integration-system.md](../design/integration-system.md)
