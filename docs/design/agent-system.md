# Agent System

**Contract owner for:** the structure of an Agent Role definition and the distinctions between roles, instances, providers, skills, tools, and workflows.

## 1. Concepts

| Concept | What it is | Where it is defined | Example |
|---|---|---|---|
| **Agent Role** | Responsibilities and authority, independent of any AI vendor | `knowledge/company/agents/<agent-id>/AGENTS.md` | `gameplay-programmer` |
| **Agent Instance** | A registered Paperclip agent fulfilling a role on a specific provider | Paperclip | "Gameplay Programmer (Codex)" |
| **AI Execution Provider** | The CLI that does the reasoning and editing | [dependencies/registry.yaml](../../dependencies/registry.yaml), integration docs | Claude Code CLI |
| **Skill** | Loadable know-how package (`SKILL.md`) | External skill packs, registered as Dependencies | Godot scene skill |
| **Tool** | Executable capability: CLI program or MCP server | Dependencies | Playwright MCP, `git`, `gh`, OpenSpec CLI |
| **Workflow** | Multi-step process across roles with gates | `knowledge/company/workflows/` | development-cycle |

Rules:
- A role MUST NOT require a specific Provider. It MAY state a *preferred* Provider in metadata.
- A role lists the Skills and Tools it may use. An Agent Instance MAY be configured with a subset.
- Workflows reference roles by Agent ID, never Agent Instances.

## 2. Required content of an Agent Role

Every `AGENTS.md` MUST contain these sections, in this order:

| Section | Content |
|---|---|
| **Identity** | ID, name, role (one line), reports to |
| **Mission** | One or two sentences: why the role exists |
| **Responsibilities** | Numbered list of concrete duties |
| **Authority** | What the role may decide alone; what it must escalate |
| **Required capabilities** | Abstract abilities (e.g. "read and write TypeScript") |
| **Tools and skills** | Allowed Tools and Skills by Dependency ID; permission profile |
| **Inputs** | What the role consumes (Task fields, documents) |
| **Outputs** | What the role produces and where |
| **Constraints** | MUST / MUST NOT rules specific to the role (studio rules apply in addition) |
| **Collaboration** | Who it works with and how (comments, sub-tasks, reviews) |
| **Escalation** | When and to whom |
| **Success criteria** | Observable conditions of good work |

## 3. Agent definition file format

Status: `APPROVED` (ADR-012, accepted 2026-11-03). YAML frontmatter compatible with the Agent Companies format, followed by the Markdown body above.

```yaml
---
slug: gameplay-programmer          # optional; Paperclip URL key, only when it differs from the directory name (knowledge/company/agents/qa uses qa-engineer)
name: Gameplay Programmer          # Agent Companies field
title: Gameplay Programmer         # Agent Companies field (Paperclip title)
reportsTo: project-manager         # Agent ID of the manager; null for the root
description: Implements gameplay systems in game repositories.
skills: []                         # Skill short names; empty until skill packs are approved
metadata:
  gameStudio:
    id: gameplay-programmer        # MUST equal the directory name
    status: active                 # active | draft | deprecated
    permissionProfile: workspace-write   # read-only | workspace-write (see security-architecture.md §4)
    preferredProviders: [claude_local, codex_local]   # superseded by `allocation` (provider-allocation.md); kept until ADR-015 is decided
    tools: [git, github-cli, openspec] # dependency IDs from dependencies/registry.yaml; `git` is assumed present
    canWriteCode: true
    allocation:                    # inputs to knowledge/company/policies/provider-allocation.md
      workType: [implementation]   # planning | implementation | review | ui-design | docs | long-context; main one first
      workload: 3                  # relative token use: implementer 3, designer/reviewer 2, others 1
      writesCode: true
      requires: []                 # e.g. [claudeSkills]
      reviews: []                  # roles whose work this role reviews
---
```

Constraints on the file:
- MUST NOT contain secrets, absolute paths, or adapter configuration (cwd, env, model).
- The body is the instruction text given to the Provider. It MUST be written in the second person ("You are …").
- Length SHOULD stay under ~300 lines; reference documents by link instead of copying them.

## 4. From role to running agent

1. Role defined in Git (this repository).
2. Board Operator registers an Agent Instance in Paperclip ([agent-onboarding.md](../../knowledge/company/workflows/agent-onboarding.md)): name, title, `reportsTo`, capabilities (from the role's description), adapter type (`claude_local` / `codex_local`, or `process` in Stage 2), adapter config (cwd strategy, model, timeout, permission flags derived from `permissionProfile`), budget.
3. Instructions: the `AGENTS.md` body is supplied to the instance (Paperclip import or adapter instruction settings, OQ-023).
4. Paperclip wakes the instance on heartbeats; each Run follows [development-cycle.md](../../knowledge/company/workflows/development-cycle.md).

**Multiple instances of one role.** To run Tasks for the same role in parallel, register additional instances (e.g. `gameplay-programmer-2`). Whether one Paperclip agent can run concurrent heartbeats for different Tasks is `UNVERIFIED` (OQ-030).

## 5. Universal agent behaviour (all roles)

Every Agent Instance MUST, on every Run:
1. Confirm its identity and the Task (Paperclip `GET /api/agents/me`, the assigned issue).
2. Check out the Task before working (atomic; a `409` means someone else owns it, so stop).
3. Read the Game Repository's `AGENTS.md` before changing it.
4. Work only in the provided Task Workspace and on its Task Branch.
5. Post a comment summarizing what it did, what remains, and links (branch, PR) before the Run ends. Paperclip enforces "comment required" (`VERIFIED`).
6. Never mark its own code change `done`; move it to `in_review`.
7. Follow [../../knowledge/company/policies/rules.md](../../knowledge/company/policies/rules.md).
8. Follow the task hygiene in [task-contract.md](../../knowledge/company/standards/task-contract.md): stay in the write set, one Task in progress, the blocker lines, record review decisions. Agents cannot read this repository at run time, so each role file repeats these rules in its own `## Task hygiene` section.

## 6. Defined roles (v1)

| Agent ID | Reports to | Permission profile | Writes code |
|---|---|---|---|
| [`director`](../../knowledge/company/agents/director/AGENTS.md) | — (root) | read-only | No |
| [`producer`](../../knowledge/company/agents/producer/AGENTS.md) | `director` | read-only | No |
| [`project-manager`](../../knowledge/company/agents/project-manager/AGENTS.md) | `producer` | read-only | No |
| [`game-designer`](../../knowledge/departments/game/agents/game-designer/AGENTS.md) | `director` | workspace-write (docs/specs only) | No |
| [`gameplay-programmer`](../../knowledge/departments/game/agents/gameplay-programmer/AGENTS.md) | `project-manager` | workspace-write | Yes |
| [`ui-designer`](../../knowledge/company/agents/ui-designer/AGENTS.md) | `project-manager` | workspace-write | Yes (UI) |
| [`qa`](../../knowledge/company/agents/qa/AGENTS.md) | `project-manager` | workspace-write (tests only) | Tests only |
| [`web-engineer`](../../knowledge/departments/web/agents/web-engineer/AGENTS.md) | `project-manager` | workspace-write (dev/test environments only) | Yes (platform projects, ADR-014) |

## Related documents
- [company-design.md](company-design.md) · [../decisions/ADR-012-agent-definition-format.md](../decisions/ADR-012-agent-definition-format.md) · [../../knowledge/company/workflows/agent-onboarding.md](../../knowledge/company/workflows/agent-onboarding.md) · [../architecture/security-architecture.md](../architecture/security-architecture.md)
