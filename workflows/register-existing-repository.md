# Workflow: Register an Existing Game Repository

- **ID:** `register-existing-repository` · **Owner:** `producer` · **Board gate:** yes

## Trigger
The Board Operator wants the studio to work on a game repository that already exists.

## Required inputs
Repository URL; Default Branch; engine and version; who else has write access.

## Actors
Board Operator, `producer`, `project-manager`, an implementer, `qa`.

## Preconditions
- Repository is reachable with the studio's GitHub credentials.
- Repository contains no secrets in its history that agents must not see (Board checks).

## Steps
1. **Board Operator** creates a Task "Register `<repo>`" assigned to `producer`, with the inputs above.
2. **`producer`** requests Board approval (payload: repository, purpose, risks) per [approval-request.md](approval-request.md).
3. **Board Operator** approves; enables branch protection on the Default Branch if missing.
4. **Board Operator** creates the Paperclip project and workspace (as in [project-initialization.md](project-initialization.md) step 5).
5. **`producer`** adds the registry entry via PR (`status: initializing`). Board merges.
6. **`project-manager`** creates an onboarding Task for an implementer: write or update the repository's `AGENTS.md`/`CLAUDE.md` (build, test, conventions, directory map) after reading the code; no functional changes.
7. **`qa`** creates a baseline Task: run the existing build and tests; report the state (pass/fail list) so later regressions are measurable.
8. After both Tasks merge, **`producer`** sets `status: active`.

## Expected outputs
Registry entry, Paperclip project, agent-ready `AGENTS.md`, baseline test report.

## Approval requirements
Step 2; registry PR; onboarding PR.

## Failure cases
| Failure | Response |
|---|---|
| Build does not work out of the box | `qa` reports; `project-manager` creates fix Tasks before feature work |
| Repository has other active human contributors | Record in `AGENTS.md`; agents must rebase on their changes and never touch their branches |
| History contains secrets | Stop; Board rotates secrets before agents get access |

## Related
[project-initialization.md](project-initialization.md) · [../docs/design/project-system.md](../docs/design/project-system.md)
