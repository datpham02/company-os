# Glossary

**Owner:** Game Studio maintainers. This is the single definition of each term. Other documents MUST use these terms with these meanings.

Terms in *italics* after a definition are the equivalent Paperclip term, when one exists.

## People and organization

| Term | Definition |
|---|---|
| **Board Operator** | The human who owns and operates the studio (currently the repository owner). Holds final approval authority. *Paperclip: board operator / board user.* |
| **Studio** | The organization defined by this repository: company, agent roles, rules, workflows. One studio runs many game projects. *Paperclip: company.* |
| **Agent Role** | A reusable role definition in `agents/<agent-id>/AGENTS.md`: mission, responsibilities, authority, constraints. Provider-independent. Lives in Git. |
| **Agent Instance** | A concrete agent registered in Paperclip that fulfils one Agent Role and is bound to one adapter/provider configuration. *Paperclip: agent.* |
| **Agent ID** | The kebab-case identifier of an Agent Role, e.g. `game-designer`. |
| **Reporting line** | The single manager an Agent Role reports to. Used for escalation. *Paperclip: `reportsTo`, chain of command.* |

## Work

| Term | Definition |
|---|---|
| **Task** | One unit of work with exactly one assignee at a time. *Paperclip: issue.* |
| **Task Key** | Human-readable task identifier from Paperclip, used in branch names. Exact format `UNVERIFIED` (OQ-004). |
| **Run** | One execution of an Agent Instance against a Task: one AI CLI process from launch to exit. *Paperclip: heartbeat run.* |
| **Heartbeat** | Paperclip's mechanism that wakes an agent for a short execution window (schedule, assignment, comment, manual, approval resolution). |
| **Workflow** | A documented, repeatable process with trigger, inputs, actors, steps, outputs, failure cases, and approval gates. Lives in `workflows/`. |
| **Approval Gate** | A step that cannot proceed without a recorded decision by an authorized approver. |
| **Approval** | The recorded decision at an Approval Gate. Recorded in Paperclip (approval or issue execution-policy stage) and, for merges, also on the GitHub pull request. |

## Projects and code

| Term | Definition |
|---|---|
| **Game Project** (or **Project**) | One game managed by the studio. Registered in `projects/project-registry.yaml` and mirrored as a Paperclip project. |
| **Project ID** | kebab-case identifier of a Game Project; equals its GitHub repository name, e.g. `node-arena`. |
| **Game Repository** | The independent Git repository holding one game's source code, e.g. `datpham02/node-arena`. |
| **Framework Repository** | This repository, `datpham02/game-studio`. Contains no game source code. |
| **Primary Checkout** | The long-lived local clone of a Game Repository on the studio machine. Agents MUST NOT work in it directly. |
| **Task Workspace** | An isolated working directory for one Task, normally a Git worktree on a dedicated Task Branch. *Paperclip: execution workspace (isolated, `git_worktree` mode).* |
| **Task Branch** | The dedicated Git branch for one Task's changes. Never the default branch. |
| **Default Branch** | The protected integration branch of a Game Repository (normally `main`). |
| **Workspace Root** | The local directory under which Primary Checkouts and Task Workspaces live. Outside the Framework Repository (ADR-010). |
| **Runtime Data** | Logs, run state, transcripts, and Task Workspaces produced by execution. Never committed to the Framework Repository. |

## Execution

| Term | Definition |
|---|---|
| **Agent Runtime** (or **Runtime**) | The planned Game Studio component that executes Tasks locally on Ubuntu. Lives in `runtime/`. `PLANNED`. |
| **Dispatcher** | Runtime sub-component that receives a Task execution request and decides whether and where to run it. |
| **Agent Launcher** | Runtime sub-component that starts and supervises the AI CLI process. |
| **Workspace Manager** | Runtime sub-component that creates, reuses, and cleans up Task Workspaces. |
| **Git Manager** | Runtime sub-component that performs Git operations under the Git safety rules. |
| **Result Reporter** | Runtime sub-component that sends Run status and results to Paperclip. |
| **AI Execution Provider** (or **Provider**) | An AI coding CLI that performs work: Claude Code CLI or Codex CLI in v1. |
| **Provider Adapter** | Runtime code that translates a generic Run request into one Provider's CLI invocation and parses its output. `PLANNED`. |
| **Paperclip Adapter** | A Paperclip package that invokes an agent runtime (`claude_local`, `codex_local`, `process`, `http`, …). Owned by Paperclip, not Game Studio. |

## Capabilities

| Term | Definition |
|---|---|
| **Skill** | A packaged, loadable capability (a `SKILL.md` directory per the Agent Skills format) that a Provider loads on demand, e.g. a Godot scene skill. Skills say *how* to do something. |
| **Tool** | An executable capability an agent can call: a CLI program or an MCP server (e.g. Playwright MCP). Tools *act*. |
| **MCP** | Model Context Protocol: the protocol AI CLIs use to call external tool servers. |
| **Dependency** | Any external project the studio relies on, recorded in `dependencies/registry.yaml`. Paperclip, Providers, Skills packs, and MCP servers are all Dependencies. |
| **Integration** | Game Studio's documented contract (and, later, adapter code) for interacting with one external system. |

## Distinctions that matter

- **Agent Role ≠ Agent Instance ≠ Provider.** `gameplay-programmer` is a Role. "Gameplay Programmer (Claude)" in Paperclip is an Instance. Claude Code CLI is the Provider that Instance runs on. One Role can have Instances on different Providers.
- **Skill ≠ Tool.** A Skill is instructions plus resources loaded into the agent's context. A Tool is something the agent calls that performs an action outside its context.
- **Workflow ≠ Task.** A Workflow is the template process. A Task is one unit of work, often one step of a Workflow instance.
- **Paperclip Adapter ≠ Provider Adapter.** The first belongs to Paperclip; the second is planned Game Studio Runtime code. See [ADR-011](decisions/ADR-011-execution-path-selection.md).

## Related documents

- [conventions.md](conventions.md)
- [design/agent-system.md](design/agent-system.md)
- [integrations/paperclip-integration.md](integrations/paperclip-integration.md)
