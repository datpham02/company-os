# Workflow: Create a New Game Project

- **ID:** `project-initialization` · **Owner:** `game-director` (proposal), `producer` (setup) · **Board gate:** yes

## Trigger
The Board Operator asks for a new game, or `game-director` proposes one.

## Required inputs
Working title; Project ID (kebab-case, unused on GitHub under `datpham02/`); concept (pitch, pillars, genre, target platform, engine preference); initial scope.

## Actors
Board Operator, `game-director`, `game-designer`, `producer`, `project-manager`, implementer (for seeding).

## Preconditions
- Paperclip is running and the studio company exists.
- No registry entry with the same Project ID.

## Steps
1. **`game-director`** writes the concept as a Paperclip issue document and requests Board approval (`request_board_approval`, payload: concept + Project ID + engine) per [approval-request.md](approval-request.md). Registry status implied: `proposed`.
2. **Board Operator** approves, requests revision, or rejects. Rejected → stop.
3. **Board Operator** creates the GitHub repository `datpham02/<project-id>` (private by default), with an initial commit on `main` (OQ-018).
4. **Board Operator** enables branch protection on `main`: require PR, require 1 approval, block force-push and deletion ([security-operations.md](../docs/operations/security-operations.md)).
5. **Board Operator** creates the Paperclip project with a workspace: `repoUrl` = repository URL, `repoRef` = `main`; sets execution workspace mode to isolated `git_worktree` (Stage 1). Records the Paperclip project ID.
6. **`producer`** opens a PR to the framework repository adding the registry entry (`status: initializing`, `paperclip.projectId`, `frameworkVersion`). Board merges it.
7. **`project-manager`** creates a seeding Task for an implementer: add `AGENTS.md` (engine, build/test commands, conventions), `CLAUDE.md` pointing to it, `.game-studio.yaml` (`PROPOSED`), `.gitignore`, and engine skeleton. Optional: `openspec init` if the project uses OpenSpec and the dependency is approved.
8. Seeding Task goes through [development-cycle.md](development-cycle.md) and [code-review-and-merge.md](code-review-and-merge.md).
9. **`game-designer`** writes vision and pillars (Task, reviewed by `game-director`).
10. **`producer`** sets registry `status: active` (PR) and creates the first milestone.

## Expected outputs
GitHub repository with protected `main`; Paperclip project; registry entry `active`; seeded repository files; vision and pillars; first milestone.

## Approval requirements
Step 2 (Board approval of the project), registry PR merge (Board), seeding PR merge (Board).

## Failure cases
| Failure | Detection | Response |
|---|---|---|
| Project ID already taken on GitHub | Step 3 | Choose new ID; update approval payload |
| Paperclip project creation fails | Step 5 | Fix and retry; registry not updated until it succeeds |
| Engine cannot run in worktrees | Seeding Task | Record in OQ-022; Board decides engine or serialized execution |
| Registry entry invalid | Schema validation (`PLANNED` script) / review | Fix in PR |

## Related
[register-existing-repository.md](register-existing-repository.md) · [../docs/design/project-system.md](../docs/design/project-system.md)
