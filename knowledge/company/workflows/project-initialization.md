# Workflow: Create a New Project

- **ID:** `project-initialization` · **Owner:** `director` (proposal), `producer` (setup) · **Board gate:** yes

## Trigger
The Board Operator asks for a new product, or `director` proposes one.

## Required inputs
Working title; Project ID (kebab-case, unused on GitHub under `datpham02/`); owning department and project type; concept in the department's format (Game: [new-game-concept.md](../../departments/game/workflows/new-game-concept.md); Web: the platform documentation set in the [Web charter](../../departments/web/README.md#platform-projects)); initial scope.

## Actors
Board Operator, `director`, the department's design role (`game-designer` for games, `ui-designer` for the website), `producer`, `project-manager`, implementer (for seeding).

## Preconditions
- Paperclip is running and the studio company exists.
- No registry entry with the same Project ID.

## Steps
1. **`director`** writes the concept as a Paperclip issue document and requests Board approval (`request_board_approval`, payload: concept + Project ID + department + stack) per [approval-request.md](approval-request.md). Registry status implied: `proposed`.
2. **Board Operator** approves, requests revision, or rejects. Rejected → stop.
3. **Board Operator** creates the GitHub repository `datpham02/<project-id>` (private by default), with an initial commit on `main` (OQ-018).
4. **Board Operator** enables branch protection on `main`: require PR, require 1 approval, block force-push and deletion ([security-operations.md](../../../docs/operations/security-operations.md)).
5. **Board Operator** creates the Paperclip project with a workspace: `repoUrl` = repository URL, `repoRef` = `main`; sets execution workspace mode to isolated `git_worktree` (Stage 1). Records the Paperclip project ID.
6. **`producer`** opens a PR to the framework repository adding the registry entry (`status: initializing`, `type`, `department`, `paperclip.projectId`, `frameworkVersion`). Board merges it.
7. **`project-manager`** creates a seeding Task for an implementer: add `AGENTS.md` (stack, build/test commands, conventions, hotspot files), `CLAUDE.md` pointing to it, `.game-studio.yaml` (`PROPOSED`), `.gitignore`, and the project skeleton. Platform projects also add the documents listed in the Web charter. Optional: `openspec init` if the project uses OpenSpec and the dependency is approved.
8. Seeding Task goes through [development-cycle.md](development-cycle.md) and [code-review-and-merge.md](code-review-and-merge.md).
9. **Department design step:** games, `game-designer` writes vision and pillars ([new-game-concept.md](../../departments/game/workflows/new-game-concept.md)); website, `director` approves the requirements and design direction. Reviewed by `director`.
10. **`producer`** sets registry `status: active` (PR) and creates the first milestone.

## Expected outputs
GitHub repository with protected `main`; Paperclip project; registry entry `active`; seeded repository files; the department's design baseline; first milestone.

## Approval requirements
Step 2 (Board approval of the project), registry PR merge (Board), seeding PR merge (Board).

## Failure cases
| Failure | Detection | Response |
|---|---|---|
| Project ID already taken on GitHub | Step 3 | Choose new ID; update approval payload |
| Paperclip project creation fails | Step 5 | Fix and retry; registry not updated until it succeeds |
| Tooling cannot run in two worktrees at once | Seeding Task | Record in OQ-022; Board decides the stack or `maxConcurrent: 1` |
| Registry entry invalid | Schema validation (`PLANNED` script) / review | Fix in PR |

## Related
[register-existing-repository.md](register-existing-repository.md) · [../../../docs/design/project-system.md](../../../docs/design/project-system.md)
