# Workflows

Canonical studio workflows. Structure contract: [../docs/design/workflow-system.md](../docs/design/workflow-system.md). Workflows are executed through Paperclip tasks, execution policies, and approvals. There is no separate workflow engine (C-004).

| # | Workflow | File | Owner role | Board gate |
|---|---|---|---|---|
| 1 | Create a new game project | [project-initialization.md](project-initialization.md) | `game-director` → `producer` | Yes |
| 2 | Register an existing game repository | [register-existing-repository.md](register-existing-repository.md) | `producer` | Yes |
| 3 | Assign an agent to a task | [task-delegation.md](task-delegation.md) | `project-manager` | No |
| 4 | Execute a task | [development-cycle.md](development-cycle.md) | Assigned implementer | Via #8 |
| 5 | Run parallel tasks | [parallel-tasks.md](parallel-tasks.md) | `project-manager` | No |
| 6 | Handle task failures | [task-failure-handling.md](task-failure-handling.md) | `project-manager` | Sometimes |
| 7 | Request approval | [approval-request.md](approval-request.md) | Any agent | Yes (it is the gate) |
| 8 | Review and merge code | [code-review-and-merge.md](code-review-and-merge.md) | `qa` + Board | Yes |
| 9 | Release a game version | [release-approval.md](release-approval.md) | `producer` | Yes |
| 10 | Add a new external dependency | [add-external-dependency.md](add-external-dependency.md) | Requesting agent | Yes |
| 11 | Add a new AI execution provider | [add-execution-provider.md](add-execution-provider.md) | Board Operator | Yes |
| 12 | Onboard a new agent | [agent-onboarding.md](agent-onboarding.md) | `game-director` / Board | Yes |
| 13 | Daily triage (`PROPOSED`) | [daily-triage.md](daily-triage.md) | `project-manager` + Board | No |

Status of all workflows: `APPROVED` as process definitions where they implement accepted ADRs; individual steps that depend on unverified Paperclip behaviour are marked `UNVERIFIED` inline.
