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
2. **`qa`** checks out the Task Branch in its own Task Workspace, builds, runs tests, verifies each acceptance criterion, and checks [../policies/rules.md](../policies/rules.md) compliance (scope, no secrets, no disabled tests). It also checks the PR's GitHub CI (`gh pr view <n> --json statusCheckRollup`): a failing or errored check blocks approval, and so does one that is still running (added 2026-11-22 after SOU-38 was approved with failing CI). This applies to every agent reviewer, not only `qa`.
3. **`qa`** records the decision: `approved` or `changes_requested`, with evidence. It also comments on the GitHub PR. `changes_requested` → Task returns to the author ([development-cycle.md](development-cycle.md) step 11).
4. After review approval, **Paperclip** moves the Task to the `approval` stage with the Board Operator as participant.
5. **Board Operator** reviews the PR in GitHub (diff, `qa` evidence). Then:
   - approves on GitHub **and** records `approved` on the Paperclip approval stage;
   - merges the PR in GitHub (merge method per repository settings, default squash `PROPOSED`).
   Or requests changes in both places.
6. **Board Operator** (or the author on its next heartbeat) moves the Task to `done` after the merge. The Task Branch MAY be deleted by GitHub's auto-delete setting.
7. Task Workspace cleanup happens per the workspace owner's rules ([runtime-architecture.md §6](../../../docs/architecture/runtime-architecture.md#6-workspace-manager)).

## Game asset Tasks
Asset and asset-integration PRs follow the same steps. `qa` checks the asset against the Task's acceptance criteria and the artist's self-check, and routes findings by owner: the look of the asset → `game-artist`; engine-side behaviour, import, shaders, performance → `gameplay-programmer`; an unclear requirement → `game-designer` ([asset-production.md](../../departments/game/workflows/asset-production.md) step 8). `qa`'s role file does not carry this routing, so whoever writes the Task puts it in the description. The creator's self-check never replaces the review.

## Pilot variant: Review Package (`PROPOSED`, Phase 6)
For code Tasks of `soucean-game` created with `pc.py create --review-package` (the first five, once the Board approves P6-B and P6-C), steps 1 to 3 change:
- the `review` stage's participant is the Board identity `local-board`, not `qa` (QA option a);
- the Board packages the PR, runs the strict read-only `code-reviewer` on its own sub-issue, and relays its verdict to the stage;
- steps 4 to 7 (approval stage, merge by the Board) stay as above.

Commands, refusals, incidents and rollback: [review-package-runbook.md](../../../docs/operations/review-package-runbook.md). Not yet run in production.

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
