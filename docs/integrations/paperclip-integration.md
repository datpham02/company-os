# Paperclip Integration

**Verified against:** Paperclip repository documentation (`docs/` directory) at commit `7b8aa60` (2026-11-03), [github.com/paperclipai/paperclip](https://github.com/paperclipai/paperclip). Latest npm package at that date: `paperclipai` 2026.1023.0. Paperclip is **not installed** on the studio machine, so nothing below has been exercised end-to-end. Labels: `VERIFIED` = stated in Paperclip's own docs; `UNVERIFIED` = assumption, tracked in [open-questions.md](../architecture/open-questions.md).

## 1. Responsibilities

| Paperclip owns (`VERIFIED` features) | Game Studio owns |
|---|---|
| Companies, goals, projects, project workspaces | Studio definition and the mapping into Paperclip |
| Agents: reporting tree, status, budgets, adapter config | Agent Role definitions (instructions, authority) |
| Issues: status lifecycle, single assignee, atomic checkout, comments, documents, sub-issues | Workflow definitions that say which issues to create |
| Heartbeats: schedule, assignment, comment mention, manual, approval resolution | — |
| Approvals; execution policies with review/approval stages | Approval *policy*: which actions need which gate |
| Adapters (`claude_local`, `codex_local`, `process`, `http`, plugins) | Choice of adapter and permission profile per Agent Instance |
| Execution workspaces (incl. isolated `git_worktree`) | Branch/workspace rules (ADR-006); Runtime for gaps (ADR-011) |
| Secrets store and bindings | Which secrets each agent may receive |
| Activity audit log, run records, costs | Run summaries in Stage 2 |

## 2. Integration boundary

Game Studio interacts with Paperclip only through:

1. **Web UI** (Board Operator).
2. **REST API**, base `http://localhost:3100/api` by default (`VERIFIED`).
3. **CLI** `paperclipai` via `npx` (`VERIFIED` commands: `onboard`, `run`, `configure`, `company export`, `company import`, `skills import`, `agent local-cli`, `allowed-hostname`).
4. **Adapters**: built-in `claude_local`, `codex_local`, `process`, `http` (all `VERIFIED`).
5. **Company packages** in the Agent Companies format (`VERIFIED`, draft spec).

Game Studio MUST NOT use undocumented endpoints or read Paperclip's database directly.

## 3. Execution paths

See [ADR-011](../decisions/ADR-011-execution-path-selection.md) (`PROPOSED`).

| Stage | Adapter | Who launches the CLI | Who creates worktrees |
|---|---|---|---|
| 1 | `claude_local` / `codex_local` | Paperclip | Paperclip (execution workspace, `git_worktree` mode) |
| 2 | `process` running the Game Studio Runtime (`PLANNED`) | Runtime | Per gap analysis (OQ-002, OQ-003) |

### 3.1 `claude_local` configuration fields (`VERIFIED`)
`cwd` (required), `model`, `promptTemplate` (variables `{{agentId}}`, `{{companyId}}`, `{{runId}}`, `{{agent.name}}`, `{{company.name}}`), `env` (supports secret refs), `timeoutSec`, `graceSec`, `maxTurnsPerRun` (default 300), `dangerouslySkipPermissions` (default `true`; see C-002). Session IDs persist between heartbeats and resume is cwd-aware. Paperclip skills are injected through a temporary directory passed with `--add-dir`.

### 3.2 `codex_local` configuration fields (`VERIFIED`)
`cwd` (required), `model`, `promptTemplate`, `env`, `timeoutSec`, `graceSec`, `fastMode`, `dangerouslyBypassApprovalsAndSandbox`; optional `instructionsFilePath` prepended to the stdin prompt sent to `codex exec`. Per-agent managed `CODEX_HOME`, seeded with the host `auth.json` (symlink) or a per-agent `OPENAI_API_KEY`. Codex may also load a repo-local `AGENTS.md`.

### 3.3 `process` adapter (`VERIFIED`)
Fields: `command` (required), `cwd`, `env`, `timeoutSec`. Paperclip injects standard environment variables (`PAPERCLIP_AGENT_ID`, `PAPERCLIP_API_KEY`, …). Exit code determines success. No session persistence.

## 4. Task synchronization

Paperclip is the system of record for Tasks; Game Studio does not keep a copy.

| Concept | Paperclip API (`VERIFIED` paths) |
|---|---|
| List / create issues | `GET`, `POST /api/companies/{companyId}/issues` |
| Read / update an issue | `GET`, `PATCH /api/issues/{issueId}` |
| Claim (atomic) | `POST /api/issues/{issueId}/checkout` with `agentId`, `expectedStatuses`; `409` = owned by another agent, **never retry** |
| Release | `POST /api/issues/{issueId}/release` |
| Comments | `GET`, `POST /api/issues/{issueId}/comments` |
| Issue documents (e.g. `plan`) | `GET /api/issues/{issueId}/documents[/{key}]` |
| Confirmations | `POST /api/issues/{issueId}/interactions` with `kind: "request_confirmation"` |

Status lifecycle (`VERIFIED`): `backlog → todo → in_progress → in_review → done`, plus `blocked`; terminal `done`, `cancelled`. Invalid transitions return `422`.

All mutating requests during a heartbeat MUST include `X-Paperclip-Run-Id` (`VERIFIED`).

## 5. Agent identity mapping

| Game Studio | Paperclip |
|---|---|
| Agent ID (`gameplay-programmer`) | Agent *name/title* and instructions; the Paperclip agent has its own UUID |
| Instance mapping | Local config `agents.<paperclip-agent-uuid>.role: <agent-id>` (Stage 2) |
| Reporting line | `reportsTo` |

Agents verify their identity with `GET /api/agents/me` (`VERIFIED`), which returns ID, company, role, chain of command, and budget.

## 6. Status reporting

- During a Run, the agent itself posts comments and updates status through the API. Paperclip enforces that every run posts a comment (execution policy "comment required", `VERIFIED`).
- The adapter records stdout, usage/cost, and session state in Paperclip's run record (`VERIFIED`).
- Stage 2: the Runtime adds a Run summary comment ([runtime-architecture.md §8](../architecture/runtime-architecture.md#8-result-reporter)).

## 7. Approval synchronization

| Need | Paperclip mechanism (`VERIFIED`) |
|---|---|
| Board approval of a governed action | `POST /api/companies/{companyId}/approvals` with `type` in `hire_agent`, `approve_ceo_strategy`, `budget_override_required`, `request_board_approval`; decisions via `/approve`, `/reject`, `/request-revision`, `/resubmit` |
| Hire an agent | `POST /api/companies/{companyId}/agent-hires` → draft agent + `hire_agent` approval |
| Review / approve a Task's work | Issue `executionPolicy.stages` of type `review` / `approval`, participants agent or user; decisions recorded with outcome `approved` / `changes_requested` |
| Wake requester on decision | Heartbeat on approval resolution; env `PAPERCLIP_APPROVAL_ID`, `PAPERCLIP_APPROVAL_STATUS`, `PAPERCLIP_LINKED_ISSUE_IDS` |

GitHub PR approval is **not** synchronized automatically (OQ-005). ADR-009 requires both records, which the Board Operator creates manually in v1.

## 8. Authentication and permissions

| Caller | Mechanism (`VERIFIED`) |
|---|---|
| Agent during heartbeat | `Authorization: Bearer $PAPERCLIP_API_KEY` (short-lived run JWT scoped to agent and run) |
| Agent outside heartbeat | Long-lived agent API key (`POST /api/agents/{agentId}/keys`; hashed at rest) |
| Board Operator | None in `local_trusted` mode (loopback only); Better Auth session in `authenticated` mode |

Company scoping: agents can access only their own company; cross-company access returns `403`.

Recommended deployment for v1: `local_trusted`, loopback bind (OQ-024).

## 9. Setup procedure (summary)

Full steps: [../operations/installation.md](../operations/installation.md).

1. Install and onboard Paperclip (`npx paperclipai onboard --yes`).
2. Create the company from [company/COMPANY.md](../../company/COMPANY.md).
3. Create agents per [company/ORGANIZATION.md](../../company/ORGANIZATION.md) and [agent-onboarding.md](../../workflows/agent-onboarding.md), `game-director` as root.
4. For each Game Project, create a Paperclip project with a workspace (`repoUrl`, `repoRef`) and record its ID in the registry.
5. Configure GitHub token as a company secret and bind it to code-writing agents.
6. Enable isolated `git_worktree` execution workspaces for projects (Stage 1).

## 10. Unverified points

OQ-001 (communication mechanism), OQ-002 (worktree ownership/paths), OQ-003 (`process` adapter context), OQ-004 (branch naming), OQ-005 (merge approval linkage), OQ-006 (root agent), OQ-007 (company import), OQ-008 (version stability), OQ-023 (instruction delivery), OQ-024 (deployment), OQ-025 (backup), OQ-029 (Paperclip Runner), OQ-030 (concurrent heartbeats per agent).

## Related documents
- [../decisions/ADR-002-paperclip-independent-orchestration.md](../decisions/ADR-002-paperclip-independent-orchestration.md) · [../decisions/ADR-011-execution-path-selection.md](../decisions/ADR-011-execution-path-selection.md) · [../architecture/data-flow.md](../architecture/data-flow.md)
