# Workflow: Execute a Task

- **ID:** `development-cycle` · **Owner:** assigned Agent Instance · **Board gate:** via [code-review-and-merge.md](code-review-and-merge.md)

## Trigger
Paperclip heartbeat for an Agent Instance with an assigned Task (assignment, comment mention, approval resolution, schedule, or manual invoke).

## Required inputs
Task (ID, acceptance criteria, project); role instructions; Game Repository `AGENTS.md`.

## Actors
Assigned agent; executor (Paperclip adapter in Stage 1, Runtime in Stage 2); `qa`; Board Operator.

## Preconditions
- Task's project is registered and `active` (or `initializing` for seeding).
- Provider CLI installed and authenticated.
- Task Workspace can be prepared (repository reachable).

## Steps
1. **Executor** prepares the Task Workspace: worktree of the Game Repository on the Task Branch, based on the latest Default Branch (new Task) or on the existing Task Branch (continuation). (Stage 1: Paperclip execution workspace. Stage 2: Runtime Workspace Manager.)
2. **Executor** launches the Provider with cwd = Task Workspace and the assembled prompt.
3. **Agent** confirms identity (`GET /api/agents/me`) and checks out the Task (`POST /api/issues/{id}/checkout`). `409` → stop without changes.
4. **Agent** reads the Task, comments, the repository `AGENTS.md`, and relevant design docs/specs.
5. **Agent** states a short plan as a Task comment. For large Tasks, it creates a `request_confirmation` on the plan and ends the Run until confirmed.
6. **Agent** implements in small commits on the Task Branch, following [../policies/rules.md](../policies/rules.md).
7. **Agent** runs the project's build and tests; fixes failures it caused.
8. **Agent** pushes the Task Branch (never the Default Branch) and opens a PR whose description links the Task and lists acceptance criteria with status.
9. **Agent** posts the Run summary comment (done / remaining / test results / links / risks) and moves the Task to `in_review`. The execution policy hands it to the `review` stage.
10. **Executor** records the run (Paperclip run record; Stage 2 also Runtime run record) and ends the process.
11. Review and approval continue in [code-review-and-merge.md](code-review-and-merge.md). If changes are requested, the Task returns to the agent and this workflow repeats from step 1 on the same Task Branch.

## Expected outputs
Commits on the Task Branch; PR; Run summary comment; Task in `in_review`; run record.

## Approval requirements
None inside this workflow; merge approval happens in workflow 8.

## Failure cases
| Failure | Response |
|---|---|
| Build/tests fail and agent cannot fix within the Task | Comment with output; Task stays `in_progress` or `blocked`; see [task-failure-handling.md](task-failure-handling.md) |
| Run times out | Work preserved on branch; next heartbeat continues |
| Push rejected (branch protection, auth) | Never force; comment; `blocked` |
| Acceptance criteria ambiguous | Comment question to `game-designer`; `blocked`; @-mention `project-manager` |
| Provider auth/quota error | Run fails; operator action ([troubleshooting.md](../../../docs/operations/troubleshooting.md)) |

## Related
[../../../docs/architecture/runtime-architecture.md](../../../docs/architecture/runtime-architecture.md) · [../../../docs/architecture/data-flow.md](../../../docs/architecture/data-flow.md)
