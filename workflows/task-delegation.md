# Workflow: Assign an Agent to a Task

- **ID:** `task-delegation` · **Owner:** `project-manager` · **Board gate:** no

## Trigger
A milestone, approved spec change, defect, or Board request needs work done.

## Required inputs
Project; goal or parent Task; acceptance criteria.

## Actors
`project-manager` (or Board Operator / `producer` for non-implementation Tasks), assignee Agent Instance.

## Preconditions
- Project is `active` (or `initializing` for seeding Tasks).
- The assignee's role is enabled for the project.

## Steps
1. **`project-manager`** writes the Task in Paperclip: title; description; acceptance criteria; affected areas/files; dependencies on other Tasks; parent issue; project.
2. Sets the **execution policy** for code Tasks: `review` stage → `qa` (or another non-author agent); `approval` stage → Board Operator user.
3. Chooses the assignee: role matches the work; Agent Instance has no Task `in_progress` (WIP limit 1); for review Tasks, not the author.
4. Checks parallel safety ([parallel-tasks.md](parallel-tasks.md)) against Tasks currently `in_progress` in the same project.
5. Assigns the Task and sets status `todo`. Paperclip wakes the assignee (assignment heartbeat, `VERIFIED`).
6. The assignee checks out the Task on its next heartbeat; execution continues in [development-cycle.md](development-cycle.md).

## Expected outputs
A Task with assignee, acceptance criteria, execution policy, and dependencies; a heartbeat for the assignee.

## Approval requirements
None. The execution policy carries the later approval gate.

## Failure cases
| Failure | Response |
|---|---|
| No suitable Agent Instance free | Leave in `todo` unassigned or queue; tell `producer` if this persists (capacity) |
| Assignee rejects Task as unclear (comment) | `project-manager` clarifies; consult `game-designer` |
| Checkout `409` | Someone else owns it; investigate duplicate assignment |

## Related
[../docs/design/workflow-system.md](../docs/design/workflow-system.md) · [../agents/project-manager/AGENTS.md](../agents/project-manager/AGENTS.md)
