# Workflow: Review and Merge Code

- **ID:** `code-review-and-merge` · **Owner:** `qa` (review), Board Operator (approval and merge) · **Board gate:** yes (ADR-009)

## Trigger
A code Task moves to `in_review` with an open PR.

## Required inputs
PR URL; Task acceptance criteria; Run summary with test results.

## Actors
`qa` (or another non-author reviewer agent), `game-designer` (optional design review), Board Operator.

## Preconditions
- PR targets the Default Branch from the Task Branch.
- Author's build/tests reported passing (or failures explained).

## Steps
1. **Paperclip** routes the Task to the `review` stage participant (`qa`), per the execution policy (`VERIFIED` mechanism).
2. **`qa`** checks out the Task Branch in its own Task Workspace, builds, runs tests, verifies each acceptance criterion, and checks [../policies/rules.md](../policies/rules.md) compliance (scope, no secrets, no disabled tests).
3. **`qa`** records the decision: `approved` or `changes_requested`, with evidence. It also comments on the GitHub PR. `changes_requested` → Task returns to the author ([development-cycle.md](development-cycle.md) step 11).
4. After review approval, **Paperclip** moves the Task to the `approval` stage with the Board Operator as participant.
5. **Board Operator** reviews the PR in GitHub (diff, `qa` evidence). Then:
   - approves on GitHub **and** records `approved` on the Paperclip approval stage;
   - merges the PR in GitHub (merge method per repository settings, default squash `PROPOSED`).
   Or requests changes in both places.
6. **Board Operator** (or the author on its next heartbeat) moves the Task to `done` after the merge. The Task Branch MAY be deleted by GitHub's auto-delete setting.
7. Task Workspace cleanup happens per the workspace owner's rules ([runtime-architecture.md §6](../../../docs/architecture/runtime-architecture.md#6-workspace-manager)).

## Expected outputs
Merged PR; Paperclip decision records for review and approval; Task `done`.

## Approval requirements
Board approval recorded in Paperclip **and** GitHub before merge. Agent reviews never substitute (ADR-009). Who clicks merge: Board Operator until OQ-016 is resolved.

## Failure cases
| Failure | Response |
|---|---|
| PR has conflicts with Default Branch | Return to author to merge `main` into the Task Branch; re-review |
| CI (if configured) fails | Treated as `changes_requested` |
| `qa` is the author | Assign another reviewer; never self-review |
| Board approves in one system only | Merge must wait until both records exist |

## Related
[../../../docs/decisions/ADR-009-approval-before-merge.md](../../../docs/decisions/ADR-009-approval-before-merge.md) · [../agents/qa/AGENTS.md](../agents/qa/AGENTS.md)
