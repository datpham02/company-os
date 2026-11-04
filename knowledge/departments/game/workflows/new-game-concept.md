# Workflow: New Game Concept

- **ID:** `new-game-concept` · **Owner:** `director` · **Board gate:** yes (inside [project-initialization.md](../../../company/workflows/project-initialization.md))
- **Extends:** the company workflow [project-initialization.md](../../../company/workflows/project-initialization.md). It adds the game-specific inputs and the design step; it never replaces the company steps.

## Trigger
The Board asks for a new game, or `director` proposes one.

## Required inputs
Working title; Project ID; pitch; pillars (three to five); genre; target platform; engine preference; initial scope.

## Steps
1. **`director`** writes the concept (pitch, pillars, genre, platform, engine, scope, risks) and checks it against [game-rules.md §1](../domain/game-rules.md#1-originality). It is the payload of step 1 of [project-initialization.md](../../../company/workflows/project-initialization.md).
2. The company workflow runs: Board approval, repository, Paperclip project, registry entry with `type: game` and `department: game`, seeding Task.
3. The seeding Task's `AGENTS.md` names the engine, build and test commands, conventions, tuning files and hotspot files ([game-rules.md §3](../domain/game-rules.md#3-default-hotspot-files)).
4. **`game-designer`** writes `docs/vision.md` (vision and pillars) in the game repository. Review: `director`.
5. **`producer`** creates the first milestone. It ends with something playable.

## Failure cases
| Failure | Response |
|---|---|
| The engine cannot run in two worktrees at once | Record in OQ-022; the Board picks another engine or `maxConcurrent: 1` |
| The concept is too close to an existing game | `director` revises the pitch before Board approval |

## Related
[../README.md](../README.md) · [../../../company/workflows/project-initialization.md](../../../company/workflows/project-initialization.md)
