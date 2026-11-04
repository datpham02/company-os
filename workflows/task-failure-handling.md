# Workflow: Handle Task Failures

- **ID:** `task-failure-handling` · **Owner:** `project-manager` · **Board gate:** only for operator actions

## Trigger
A Run ends unsuccessfully, a Task is set to `blocked`, or the [daily triage](daily-triage.md) lists it (time limits in [task-contract.md §7](../docs/design/task-contract.md#7-liveness-nothing-is-forgotten)).

## Required inputs
Task history: comments, run records, exit class, branch state.

## Actors
Failing agent; `project-manager`; Board Operator (for environment problems).

## Preconditions
None.

## Steps
1. **Classify** using the last Run's outcome ([runtime-architecture.md §10](../docs/architecture/runtime-architecture.md#10-error-handling)):
   - *Environment* (auth, quota, tool missing, Paperclip/GitHub unreachable) → step 2.
   - *Task* (unclear requirements, design conflict, out of authority, missing context) → step 3.
   - *Dependency* (waits for another Task) → make sure a blocker relation exists; Paperclip wakes the Task when every blocker is `done`. A **cancelled** blocker never resolves: point the relation at the replacement Task or remove it.
   - *Review tooling* (the reviewer ended without a recorded decision) → wake the reviewer once; then the Board records a manual resolution or reassigns the review.
   - *Execution* (build/test failures, agent stuck, timeout) → step 4.
2. **Environment:** `project-manager` comments the diagnosis and creates a Task for the Board Operator (or requests confirmation) with the fix needed (e.g. "log in to Codex"). Task stays `blocked` until fixed. No retries meanwhile.
3. **Task:** route the question to the owning role (`game-designer` for design, `producer` for scope). After the answer, unblock and the agent continues on the same branch.
4. **Execution:** allow automatic continuation on the next heartbeat up to **3 consecutive unsuccessful Runs**. After the third:
   a. `project-manager` reads the run logs and comments.
   b. Chooses: split the Task, add guidance, reassign to another Agent Instance (possibly another Provider), or escalate to `producer`.
   c. Work on the existing branch is preserved; the new assignee continues from it unless the plan says to restart.
5. **Record** the failure cause in the Task (one-line "Failure cause" comment) so recurring causes are visible in reports. Every blocked Task keeps a named unblock owner and a next check until it moves on.

## Expected outputs
Task back in progress with a plan, or explicitly `cancelled` with reason; environment issues turned into operator Tasks.

## Approval requirements
Cancelling a Task that is part of an approved milestone requires `producer` agreement; environment changes requiring new credentials or permissions require Board approval.

## Failure cases
| Failure | Response |
|---|---|
| Same failure recurs across Tasks | `producer` raises a process/infra Task; Board informed |
| Branch in an inconsistent state | Agent never resets shared history; creates a new Task Branch from the last good commit and documents it |

## Related
[../docs/design/workflow-system.md §6](../docs/design/workflow-system.md#6-failure-and-retry-handling) · [../docs/operations/troubleshooting.md](../docs/operations/troubleshooting.md)
