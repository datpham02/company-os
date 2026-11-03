# Workflow: Release a Game Version

- **ID:** `release-approval` · **Owner:** `producer` · **Board gate:** yes

## Trigger
A milestone marked as a release is complete, or the Board requests a release.

## Required inputs
Version number (SemVer `MAJOR.MINOR.PATCH`, `PROPOSED`); list of merged Tasks/PRs; target platforms.

## Actors
`producer`, `qa`, `project-manager`, Board Operator.

## Preconditions
- All Tasks in the release scope are `done` (merged).
- No open defects of severity "blocker" for this project.

## Steps
1. **`producer`** creates a release Task with scope and version.
2. **`qa`** runs the regression and acceptance checks on the Default Branch head in a Task Workspace; posts a test report.
3. **`project-manager`** (via an implementer Task) prepares a release PR: version bump in project files, `CHANGELOG.md` entry. Goes through [code-review-and-merge.md](code-review-and-merge.md).
4. **`producer`** requests Board approval (`request_board_approval`) with: version, changelog, `qa` report, known issues, commit SHA to release.
5. **Board Operator** approves.
6. **Board Operator** creates the annotated tag `v<version>` on the approved SHA and the GitHub release (UI or `gh release create`). Agents do not tag in v1.
7. Build artifacts and store/distribution publishing are project-specific and out of scope for v1 (documented per game in its `AGENTS.md`).
8. **`producer`** closes the milestone and the release Task; updates registry `status` if the game moves to `maintenance`.

## Expected outputs
Tag `v<version>`, GitHub release, `qa` report, Board decision record.

## Approval requirements
Step 4–5 (Board), plus the release PR merge.

## Failure cases
| Failure | Response |
|---|---|
| `qa` finds a blocker | Release stops; fix Tasks created; restart at step 2 |
| Board rejects | `producer` records the reason; re-plan |
| Wrong SHA tagged | Board deletes the tag manually and re-tags (destructive operation: human only) |

## Related
[../agents/producer/AGENTS.md](../agents/producer/AGENTS.md) · [code-review-and-merge.md](code-review-and-merge.md)
