# Operating Model

How the studio runs day to day. Processes are defined in [workflows/](workflows/); this file describes the rhythm and the operator's touchpoints.

## 1. Control surfaces
- **Board Operator** uses the Paperclip web UI for goals, tasks, approvals, monitoring, and budgets, and uses GitHub to review and merge pull requests. The operator does not need to open game workspaces.
- **Agents** are woken by Paperclip heartbeats and act through their Provider in a Task Workspace.
- **Delivery:** When the Board explicitly authorizes repository delivery, changes finish as a **Draft** GitHub PR on a feature branch (never auto-merged; write-set only). Policy: [policies/pull-request-delivery.md](policies/pull-request-delivery.md) §0–§1; root `AGENTS.md` §3 rule 8.

## 2. Work intake
1. The Board sets studio and project goals in Paperclip.
2. `director` turns goals into direction; `producer` turns direction into milestones; `project-manager` turns milestones into Tasks ([task-delegation.md](workflows/task-delegation.md)).
3. Implementers execute Tasks ([development-cycle.md](workflows/development-cycle.md)).
4. `qa` reviews; the Board approves and merges ([code-review-and-merge.md](workflows/code-review-and-merge.md)).

## 3. Cadence (`PROPOSED`, configured as Paperclip scheduled heartbeats)
| Cadence | Who | Output |
|---|---|---|
| On assignment | Any agent | Task progress |
| Daily | `project-manager` | Per-project status comment: done, in progress, blocked |
| Weekly | `producer` | Studio status report and milestone forecast for the Board |
| Per milestone | `director` | Direction review: games against their pillars, the website against its approved scope and design direction |

## 4. Work-in-progress limits (`PROPOSED`)
- Max 2 concurrent Runs on the machine (OQ-015).
- Max 1 Task in progress per Agent Instance.
- `project-manager` keeps at most 5 open `in_review` Tasks per project before assigning new implementation work, so review does not pile up.

## 5. Budgets
Paperclip budgets per agent (soft warning, hard pause at 100%, `VERIFIED` Paperclip feature). The Board sets them at agent registration; overrides need `budget_override_required` approval.

## 6. Multi-project operation
- Agent Instances serve all active projects unless a project restricts roles.
- `producer` balances priorities across projects; `project-manager` plans within one project at a time per Task.
- Each project's status is visible as its own Paperclip project.
