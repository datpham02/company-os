# Workflow: Run Parallel Tasks

- **ID:** `parallel-tasks` · **Owner:** `project-manager` · **Board gate:** no

## Trigger
More than one Task in the same project is ready and agents are available.

## Required inputs
Candidate Tasks with "affected areas/files"; current `in_progress` Tasks; concurrency limits.

## Actors
`project-manager`; assigned agents; executor.

## Preconditions
- Each candidate Task has a write set ([task-contract.md §2](../standards/task-contract.md#2-task-contract)).
- Machine concurrency limit not reached (default 2 concurrent Runs, OQ-015).

## Steps
1. **`project-manager`** compares the write sets of candidate Tasks with each other and with **every unmerged Task** of the project: `in_progress`, `in_review`, `blocked`, and approved but not merged. (GAM-44 was in review, not yet merged, when GAM-45 started on the same scene file; the second PR then conflicted.)
2. Overlap (same files, same scene/asset, same config, schema/data migrations, or a hotspot file listed in the repository's `AGENTS.md`) → add a Paperclip blocker relation from the later Task to the earlier one and do not start it. Fix and follow-up Tasks on the same files are blocked by the parent's merge.
3. No overlap → assign to different Agent Instances, one `in_progress` Task per instance. A busy agent's next Task waits. Multiple instances of one role may be needed (OQ-030).
4. **Executor** gives each Task its own Task Workspace (worktree) and Task Branch (ADR-006). Never two Runs in one workspace.
5. Each Task follows [development-cycle.md](development-cycle.md) independently.
6. Merge order: the Board merges PRs one at a time, in dependency order. After each merge the `project-manager` comments on every open PR whose write set overlaps the merged change. After each merge, agents with open PRs on the same project rebase or merge the new Default Branch into their Task Branch on their next Run, re-run tests, and push. Never force-push a branch under review. Prefer a merge commit from `main` into the Task Branch.

## Expected outputs
Concurrent Runs in isolated worktrees; PRs that merge without conflicts.

## Approval requirements
None beyond each Task's own.

## Failure cases
| Failure | Response |
|---|---|
| Merge conflict discovered after all | The later Task's agent resolves on its branch; `qa` re-reviews |
| Engine cannot open two worktrees concurrently (lock files, caches) | Serialize Tasks for that project; record in registry `workflows.parallel-tasks.maxConcurrent: 1` |
| Machine overloaded | Lower concurrency limit |

## Related
[../../../docs/decisions/ADR-006-git-worktree-for-concurrent-tasks.md](../../../docs/decisions/ADR-006-git-worktree-for-concurrent-tasks.md) · [../docs/architecture/runtime-architecture.md §12](../../../docs/architecture/runtime-architecture.md#12-concurrent-execution)
